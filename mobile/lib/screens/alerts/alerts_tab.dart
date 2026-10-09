import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/constants.dart';
import '../../models/alert_item.dart';
import '../../providers/app_providers.dart';
import '../../widgets/metric_card.dart';

class AlertsTab extends ConsumerStatefulWidget {
  const AlertsTab({super.key});

  @override
  ConsumerState<AlertsTab> createState() => _AlertsTabState();
}

class _AlertsTabState extends ConsumerState<AlertsTab> {
  bool onlyUnread = false;

  @override
  Widget build(BuildContext context) {
    final alerts = ref.watch(alertsProvider);
    final unreadCount = alerts.where((a) => !a.read).length;

    final visible = onlyUnread ? alerts.where((a) => !a.read).toList() : alerts;

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(alertsProvider.notifier).refresh();
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Water Alerts',
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                      color: jalosInk,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    unreadCount > 0
                        ? '$unreadCount unread notice${unreadCount > 1 ? 's' : ''}'
                        : 'All alerts caught up',
                    style: TextStyle(
                      color: unreadCount > 0 ? jalosGreen : jalosMuted,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              FilterChip(
                label: const Text('Unread Only'),
                selected: onlyUnread,
                onSelected: (val) => setState(() => onlyUnread = val),
                selectedColor: jalosGreenLight,
                labelStyle: TextStyle(
                  fontSize: 11,
                  color: onlyUnread ? jalosGreen : jalosMuted,
                  fontWeight:
                      onlyUnread ? FontWeight.w700 : FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (visible.isEmpty)
            metricCard(
              child: const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(vertical: 24),
                  child: Column(
                    children: [
                      Icon(Icons.notifications_none_rounded,
                          color: jalosMuted, size: 36),
                      SizedBox(height: 8),
                      Text(
                        'No notifications',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: jalosInk,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'Important updates and society shortages will appear here.',
                        style: TextStyle(fontSize: 12, color: jalosMuted),
                      ),
                    ],
                  ),
                ),
              ),
            )
          else
            ...visible.map((a) => Padding(
                  padding: const EdgeInsets.only(bottom: 9),
                  child: _alertCard(context, ref, a),
                )),
        ],
      ),
    );
  }

  Widget _alertCard(BuildContext context, WidgetRef ref, AlertItem item) {
    final isCritical =
        item.level == 'CRITICAL' || item.level == 'HIGH';

    return metricCard(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: isCritical ? jalosCriticalBg : jalosMint,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              isCritical
                  ? Icons.warning_amber_rounded
                  : Icons.water_drop_outlined,
              color: isCritical ? jalosCriticalText : jalosGreen,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      item.level,
                      style: TextStyle(
                        fontSize: 9,
                        letterSpacing: 0.6,
                        fontWeight: FontWeight.w800,
                        color: isCritical ? jalosCriticalText : jalosGreen,
                      ),
                    ),
                    Text(
                      item.createdAt,
                      style: const TextStyle(
                          fontSize: 10, color: jalosMuted),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  item.message,
                  style: TextStyle(
                    fontSize: 13,
                    height: 1.4,
                    color: item.read ? const Color(0xFF65756E) : jalosInk,
                    fontWeight:
                        item.read ? FontWeight.w500 : FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          if (!item.read)
            IconButton(
              icon: const Icon(Icons.mark_email_read_outlined, size: 20),
              color: jalosGreen,
              tooltip: 'Mark as read',
              onPressed: () {
                ref.read(alertsProvider.notifier).markAsRead(item.id);
              },
            )
          else
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: Icon(Icons.check, size: 16, color: jalosMuted),
            ),
        ],
      ),
    );
  }
}
