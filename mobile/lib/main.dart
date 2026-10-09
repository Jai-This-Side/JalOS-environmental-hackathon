import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/constants.dart';
import 'screens/splash_gate.dart';

export 'widgets/animated_tank.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const JalOSApp());
}

class JalOSApp extends StatelessWidget {
  const JalOSApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'JalOS',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: jalosGreen,
            surface: jalosBg,
          ),
          useMaterial3: true,
          scaffoldBackgroundColor: jalosBg,
          fontFamily: 'Roboto',
        ),
        home: const SplashGate(),
      ),
    );
  }
}
