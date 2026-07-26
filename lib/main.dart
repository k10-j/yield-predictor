import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

/// -----------------------------------------------------------------------
/// Point this at your deployed FastAPI base URL (Task 2). For local testing
/// against `uvicorn main:app --host 0.0.0.0 --port 8000` running on your
/// computer:
///   - Android emulator  -> http://10.0.2.2:8000
///   - iOS simulator     -> http://127.0.0.1:8000
///   - Physical device   -> http://<your-computer-LAN-IP>:8000
///   - Chrome/web build  -> http://localhost:8000
/// Once deployed (e.g. on Render), replace this with the public URL, e.g.
///   https://crop-yield-api.onrender.com
/// -----------------------------------------------------------------------
const String apiBaseUrl = "http://10.0.2.2:8000";

void main() {
  runApp(const CropYieldApp());
}

class CropYieldApp extends StatelessWidget {
  const CropYieldApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Crop Yield Predictor',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: Colors.green, useMaterial3: true),
      home: const PredictorPage(),
    );
  }
}

/// Holds everything the form needs, fetched once from GET /metadata:
/// the exact list of supported countries/crops and the numeric ranges the
/// API will enforce, so client-side validation matches server-side exactly.
class _Metadata {
  final List<String> areas;
  final List<String> items;
  final Map<String, dynamic> ranges;
  final String modelUsed;

  _Metadata({
    required this.areas,
    required this.items,
    required this.ranges,
    required this.modelUsed,
  });

  factory _Metadata.fromJson(Map<String, dynamic> json) => _Metadata(
        areas: List<String>.from(json["areas"]),
        items: List<String>.from(json["items"]),
        ranges: Map<String, dynamic>.from(json["ranges"]),
        modelUsed: json["model_used"],
      );

  double _min(String key) => (ranges[key]["min"] as num).toDouble();
  double _max(String key) => (ranges[key]["max"] as num).toDouble();
}

class PredictorPage extends StatefulWidget {
  const PredictorPage({super.key});

  @override
  State<PredictorPage> createState() => _PredictorPageState();
}

class _PredictorPageState extends State<PredictorPage> {
  final _formKey = GlobalKey<FormState>();

  final _yearController = TextEditingController();
  final _rainController = TextEditingController();
  final _pesticidesController = TextEditingController();
  final _tempController = TextEditingController();

  String? _selectedArea;
  String? _selectedItem;

  Future<_Metadata>? _metadataFuture;
  bool _isPredicting = false;
  String? _resultText;
  bool _isError = false;

  @override
  void initState() {
    super.initState();
    _metadataFuture = _loadMetadata();
  }

  @override
  void dispose() {
    _yearController.dispose();
    _rainController.dispose();
    _pesticidesController.dispose();
    _tempController.dispose();
    super.dispose();
  }

  Future<_Metadata> _loadMetadata() async {
    final response = await http
        .get(Uri.parse("$apiBaseUrl/metadata"))
        .timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) {
      throw Exception("Server returned ${response.statusCode}");
    }
    return _Metadata.fromJson(jsonDecode(response.body));
  }

  Future<void> _predict(_Metadata meta) async {
    setState(() {
      _resultText = null;
      _isError = false;
    });

    if (!_formKey.currentState!.validate() ||
        _selectedArea == null ||
        _selectedItem == null) {
      setState(() {
        _isError = true;
        _resultText = "Please fix the highlighted fields before predicting.";
      });
      return;
    }

    final body = {
      "area": _selectedArea,
      "item": _selectedItem,
      "year": int.parse(_yearController.text),
      "average_rain_fall_mm_per_year": double.parse(_rainController.text),
      "pesticides_tonnes": double.parse(_pesticidesController.text),
      "avg_temp": double.parse(_tempController.text),
    };

    setState(() => _isPredicting = true);

    try {
      final response = await http
          .post(
            Uri.parse("$apiBaseUrl/predict"),
            headers: {"Content-Type": "application/json"},
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 15));

      final decoded = jsonDecode(response.body);

      if (response.statusCode == 200) {
        final yieldValue = decoded["predicted_yield_tonnes_per_ha"];
        final model = decoded["model_used"];
        setState(() {
          _isError = false;
          _resultText = "Predicted Yield: $yieldValue tonnes/ha\n(model: $model)";
        });
      } else {
        setState(() {
          _isError = true;
          _resultText = "Error from server: ${_extractApiError(decoded)}";
        });
      }
    } catch (e) {
      setState(() {
        _isError = true;
        _resultText =
            "Could not reach the prediction API.\nCheck apiBaseUrl and your "
            "network connection.\n($e)";
      });
    } finally {
      setState(() => _isPredicting = false);
    }
  }

  String _extractApiError(dynamic decoded) {
    final detail = decoded["detail"];
    if (detail is String) return detail;
    if (detail is List && detail.isNotEmpty) {
      return detail
          .map((d) => d is Map ? "${d["loc"]?.last}: ${d["msg"]}" : d.toString())
          .join("; ");
    }
    return decoded.toString();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Crop Yield Predictor")),
      body: SafeArea(
        child: FutureBuilder<_Metadata>(
          future: _metadataFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError || !snapshot.hasData) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.cloud_off, size: 40, color: Colors.red),
                      const SizedBox(height: 12),
                      Text(
                        "Couldn't load the country/crop list from the API.\n"
                        "Check apiBaseUrl (currently set to $apiBaseUrl) and "
                        "that the server is running.\n\n${snapshot.error}",
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 16),
                      FilledButton(
                        onPressed: () =>
                            setState(() => _metadataFuture = _loadMetadata()),
                        child: const Text("Retry"),
                      ),
                    ],
                  ),
                ),
              );
            }

            final meta = snapshot.data!;
            return _buildForm(meta);
          },
        ),
      ),
    );
  }

  Widget _buildForm(_Metadata meta) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              "Enter region & field conditions",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              "Model in use: ${meta.modelUsed}",
              style: const TextStyle(color: Colors.black54),
            ),
            const SizedBox(height: 16),

            DropdownButtonFormField<String>(
              value: _selectedArea,
              isExpanded: true,
              decoration: const InputDecoration(
                labelText: "Country (Area)",
                border: OutlineInputBorder(),
                isDense: true,
              ),
              items: meta.areas
                  .map((a) => DropdownMenuItem(value: a, child: Text(a)))
                  .toList(),
              onChanged: (v) => setState(() => _selectedArea = v),
              validator: (v) => v == null ? "Please select a country" : null,
            ),
            const SizedBox(height: 12),

            DropdownButtonFormField<String>(
              value: _selectedItem,
              isExpanded: true,
              decoration: const InputDecoration(
                labelText: "Crop (Item)",
                border: OutlineInputBorder(),
                isDense: true,
              ),
              items: meta.items
                  .map((i) => DropdownMenuItem(value: i, child: Text(i)))
                  .toList(),
              onChanged: (v) => setState(() => _selectedItem = v),
              validator: (v) => v == null ? "Please select a crop" : null,
            ),
            const SizedBox(height: 12),

            _numberField(
              controller: _yearController,
              label: "Year",
              min: meta._min("year"),
              max: meta._max("year"),
              allowDecimal: false,
            ),
            const SizedBox(height: 12),
            _numberField(
              controller: _rainController,
              label: "Rainfall (mm/year)",
              min: meta._min("average_rain_fall_mm_per_year"),
              max: meta._max("average_rain_fall_mm_per_year"),
            ),
            const SizedBox(height: 12),
            _numberField(
              controller: _pesticidesController,
              label: "Pesticides (tonnes)",
              min: meta._min("pesticides_tonnes"),
              max: meta._max("pesticides_tonnes"),
            ),
            const SizedBox(height: 12),
            _numberField(
              controller: _tempController,
              label: "Average Temperature (°C)",
              min: meta._min("avg_temp"),
              max: meta._max("avg_temp"),
            ),

            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: _isPredicting ? null : () => _predict(meta),
              icon: _isPredicting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.eco),
              label: Text(_isPredicting ? "Predicting..." : "Predict"),
              style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 14)),
            ),

            const SizedBox(height: 20),
            if (_resultText != null)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: _isError ? Colors.red.shade50 : Colors.green.shade50,
                  border: Border.all(color: _isError ? Colors.red : Colors.green),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  _resultText!,
                  style: TextStyle(
                    fontSize: 16,
                    color: _isError ? Colors.red.shade900 : Colors.green.shade900,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _numberField({
    required TextEditingController controller,
    required String label,
    required double min,
    required double max,
    bool allowDecimal = true,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: TextInputType.numberWithOptions(decimal: allowDecimal, signed: true),
      decoration: InputDecoration(
        labelText: label,
        hintText: "${min.toStringAsFixed(0)} - ${max.toStringAsFixed(0)}",
        border: const OutlineInputBorder(),
        isDense: true,
      ),
      validator: (value) {
        if (value == null || value.trim().isEmpty) return "$label is required";
        final parsed = double.tryParse(value);
        if (parsed == null) return "Enter a valid number";
        if (parsed < min || parsed > max) {
          return "Must be between ${min.toStringAsFixed(0)} and ${max.toStringAsFixed(0)}";
        }
        return null;
      },
    );
  }
}