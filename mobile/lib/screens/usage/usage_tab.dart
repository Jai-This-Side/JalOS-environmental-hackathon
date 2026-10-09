import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/constants.dart';
import '../../models/usage.dart';
import '../../providers/app_providers.dart';
import '../../widgets/consumption_charts.dart';
import '../../widgets/metric_card.dart';

class UsageTab extends ConsumerStatefulWidget {
  const UsageTab({super.key});

  @override
  ConsumerState<UsageTab> createState() => _UsageTabState();
}

class _UsageTabState extends ConsumerState<UsageTab> {
  String selectedWindow = '7 days';

  @override
  Widget build(BuildContext context) {
    final usageAsync = ref.watch(usageProvider);

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(usageProvider.notifier).refresh();
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          const Text(
            'Household Consumption',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w800,
              color: jalosInk,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 2),
          const Text(
            'Private virtual-meter readings · synthetic prototype data',
            style: TextStyle(color: jalosMuted, fontSize: 12),
          ),
          const SizedBox(height: 14),
          usageAsync.when(
            loading: () => const Center(
              child: Padding(
                padding: EdgeInsets.symmetric(vertical: 40),
                child: CircularProgressIndicator(),
              ),
            ),
            error: (err, _) => metricCard(
              child: const Text(
                'Could not load consumption history. Check connection.',
                style: TextStyle(color: jalosCriticalText),
              ),
            ),
            data: (usage) => _buildUsageContent(context, usage),
          ),
        ],
      ),
    );
  }

  Widget _buildUsageContent(BuildContext context, HouseholdUsage usage) {
    final range = usage.recommendedRange;
    final rangeStr = range.length >= 2
        ? '${range[0].round()}–${range[1].round()} L/day'
        : '350–500 L/day';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        metricCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'TODAY SO FAR',
                        style: TextStyle(
                          fontSize: 10,
                          letterSpacing: 0.8,
                          color: jalosMuted,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${usage.todayLitres.round()} Litres',
                        style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w900,
                          color: jalosInk,
                        ),
                      ),
                    ],
                  ),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: jalosGreenLight,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      'Flat ${usage.flatId}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: jalosGreen,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Divider(height: 1, color: Color(0xFFF0F4F2)),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _subMetric(
                      'Yesterday',
                      '${usage.yesterdayLitres.round()} L',
                    ),
                  ),
                  Expanded(
                    child: _subMetric(
                      '7-Day Average',
                      '${usage.sevenDayAverageLitres?.round() ?? '—'} L/day',
                    ),
                  ),
                  Expanded(
                    child: _subMetric(
                      '30-Day Average',
                      '${usage.thirtyDayAverageLitres?.round() ?? '—'} L/day',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF9FCFB),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE5EFEA)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.eco_outlined,
                        color: jalosGreen, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Dynamic Water Budget: $rangeStr',
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: jalosInk,
                            ),
                          ),
                          const SizedBox(height: 2),
                          const Text(
                            'Smart guidance adjusted for society water risk, not a strict cap.',
                            style: TextStyle(
                              fontSize: 10,
                              color: jalosMuted,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        metricCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Consumption Profile',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 15,
                  color: jalosInk,
                ),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                children: ['Today', 'Yesterday', '7 days', '30 days']
                    .map(
                      (w) => ChoiceChip(
                        label: Text(w),
                        selected: selectedWindow == w,
                        onSelected: (_) => setState(() => selectedWindow = w),
                        selectedColor: jalosGreenLight,
                        labelStyle: TextStyle(
                          color: selectedWindow == w ? jalosGreen : jalosMuted,
                          fontSize: 11,
                          fontWeight: selectedWindow == w
                              ? FontWeight.w700
                              : FontWeight.w500,
                        ),
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: 14),
              ConsumptionChart(
                usage: usage,
                window: selectedWindow,
              ),
              if (usage.possibleAnomaly) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: jalosCriticalBg,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.warning_amber_rounded,
                          color: jalosCriticalText, size: 20),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Possible anomaly in recent household readings. This is a review signal, not a confirmed leak.',
                          style: TextStyle(
                            color: jalosCriticalText,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _subMetric(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 10, color: jalosMuted),
        ),
        const SizedBox(height: 3),
        Text(
          value,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: jalosInk,
          ),
        ),
      ],
    );
  }
}
