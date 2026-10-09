import 'package:flutter/material.dart';

const String apiBase = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000/api/v1',
);

const String socketBase = String.fromEnvironment(
  'WEBSOCKET_URL',
  defaultValue: 'ws://localhost:8000/ws/societies/demo',
);

// JalOS Brand Theme Palette
const Color jalosInk = Color(0xFF173B31);
const Color jalosGreen = Color(0xFF159A7D);
const Color jalosGreenLight = Color(0xFFDDF2E9);
const Color jalosMint = Color(0xFFEAF5F2);
const Color jalosBg = Color(0xFFF5F8F6);
const Color jalosCardBorder = Color(0xFFE8EFEB);
const Color jalosMuted = Color(0xFF81928A);
const Color jalosTextDark = Color(0xFF223830);

// Risk Colors
const Color jalosCriticalBg = Color(0xFFFFEFEA);
const Color jalosCriticalText = Color(0xFFB95643);
const Color jalosModerateBg = Color(0xFFFFF7E6);
const Color jalosModerateText = Color(0xFFB57D18);
const Color jalosNormalBg = Color(0xFFEAF6EF);
const Color jalosNormalText = Color(0xFF398468);
