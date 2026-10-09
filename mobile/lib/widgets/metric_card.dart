import 'package:flutter/material.dart';
import '../core/constants.dart';

Widget metricCard({required Widget child, EdgeInsetsGeometry? padding}) {
  return Container(
    padding: padding ?? const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(18),
      border: Border.all(color: jalosCardBorder),
    ),
    child: child,
  );
}

Widget statTile({
  required String label,
  required String value,
  required IconData icon,
  String? subtext,
}) {
  return metricCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: jalosGreen, size: 20),
        const SizedBox(height: 10),
        Text(
          label.toUpperCase(),
          style: const TextStyle(
            fontSize: 9,
            letterSpacing: 0.65,
            color: jalosMuted,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 18,
            color: jalosInk,
          ),
        ),
        if (subtext != null) ...[
          const SizedBox(height: 2),
          Text(
            subtext,
            style: const TextStyle(fontSize: 10, color: jalosMuted),
          ),
        ]
      ],
    ),
  );
}

Widget riskChip(String risk) {
  final upper = risk.toUpperCase();
  final isCritical = upper == 'CRITICAL' || upper == 'HIGH';
  final isModerate = upper == 'MODERATE';

  final bg = isCritical
      ? jalosCriticalBg
      : isModerate
          ? jalosModerateBg
          : jalosNormalBg;

  final text = isCritical
      ? jalosCriticalText
      : isModerate
          ? jalosModerateText
          : jalosNormalText;

  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(
      color: bg,
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(
      '$upper RISK',
      style: TextStyle(
        fontSize: 9,
        color: text,
        fontWeight: FontWeight.w800,
        letterSpacing: 0.4,
      ),
    ),
  );
}
