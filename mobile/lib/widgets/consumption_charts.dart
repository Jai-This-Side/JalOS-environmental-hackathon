import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../core/constants.dart';
import '../models/usage.dart';

class ConsumptionChart extends StatelessWidget {
  final HouseholdUsage usage;
  final String window;

  const ConsumptionChart({
    super.key,
    required this.usage,
    required this.window,
  });

  @override
  Widget build(BuildContext context) {
    if (window == 'Today' || window == 'Yesterday') {
      return _buildHourlyChart(context);
    }
    return _buildDailyChart(context);
  }

  Widget _buildHourlyChart(BuildContext context) {
    final points =
        window == 'Today' ? usage.hourlyToday : usage.hourlyYesterday;

    if (points.isEmpty) {
      return const SizedBox(
        height: 200,
        child: Center(
          child: Text(
            'Reading virtual meter telemetry for this period…',
            style: TextStyle(color: jalosMuted, fontSize: 12),
          ),
        ),
      );
    }

    final maxVal = points.fold<double>(
      0.0,
      (max, p) => p.litres > max ? p.litres : max,
    );
    final chartMax = (maxVal * 1.25).clamp(15.0, 1000.0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 210,
          child: LineChart(
            LineChartData(
              minY: 0,
              maxY: chartMax,
              gridData: const FlGridData(show: true, drawVerticalLine: false),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 22,
                    interval: 4,
                    getTitlesWidget: (val, meta) {
                      final h = val.toInt();
                      if (h % 4 == 0 && h < 24) {
                        return Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(
                            '$h:00',
                            style: const TextStyle(
                                fontSize: 9, color: jalosMuted),
                          ),
                        );
                      }
                      return const SizedBox.shrink();
                    },
                  ),
                ),
              ),
              lineBarsData: [
                LineChartBarData(
                  isCurved: true,
                  color: jalosGreen,
                  barWidth: 2.8,
                  dotData: FlDotData(
                    show: true,
                    getDotPainter: (spot, percent, barData, index) {
                      final isAnomaly = index < points.length && points[index].anomaly;
                      if (isAnomaly) {
                        return FlDotCirclePainter(
                          radius: 5.5,
                          color: const Color(0xFFE0533C),
                          strokeWidth: 2,
                          strokeColor: Colors.white,
                        );
                      }
                      return FlDotCirclePainter(
                        radius: 2,
                        color: jalosGreen,
                        strokeWidth: 0,
                      );
                    },
                  ),
                  belowBarData: BarAreaData(
                    show: true,
                    color: jalosGreen.withValues(alpha: 0.08),
                  ),
                  spots: [
                    for (int i = 0; i < points.length; i++)
                      FlSpot(points[i].hour.toDouble(), points[i].litres)
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 12,
          runSpacing: 4,
          children: [
            _legend(jalosGreen, 'Hourly usage (L)'),
            if (points.any((p) => p.anomaly))
              _legend(const Color(0xFFE0533C), 'Unusual consumption spot'),
          ],
        ),
      ],
    );
  }

  Widget _buildDailyChart(BuildContext context) {
    final windowDays = window == '30 days' ? 30 : 7;
    final allSeries = usage.dailySeries;
    final visibleSeries = allSeries.length > windowDays
        ? allSeries.sublist(allSeries.length - windowDays)
        : allSeries;

    if (visibleSeries.isEmpty) {
      return const SizedBox(
        height: 200,
        child: Center(
          child: Text(
            'Usage history is building from virtual meter readings…',
            style: TextStyle(color: jalosMuted, fontSize: 12),
          ),
        ),
      );
    }

    final maxVal = visibleSeries.fold<double>(
      0.0,
      (max, p) => p.litres > max ? p.litres : max,
    );
    final baseline = usage.householdBaselineLitresPerDay;
    final range = usage.recommendedRange;

    final chartMax = [
      maxVal,
      baseline,
      if (range.length > 1) range[1],
    ].reduce((a, b) => a > b ? a : b) * 1.18;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 210,
          child: LineChart(
            LineChartData(
              minY: 0,
              maxY: chartMax > 0 ? chartMax : null,
              gridData: const FlGridData(show: true, drawVerticalLine: false),
              borderData: FlBorderData(show: false),
              extraLinesData: ExtraLinesData(horizontalLines: [
                HorizontalLine(
                  y: baseline,
                  color: const Color(0xFF8D86C5),
                  strokeWidth: 1.2,
                  dashArray: [4, 4],
                ),
                if (range.isNotEmpty)
                  HorizontalLine(
                    y: range[0],
                    color: const Color(0xFF82B89F),
                    strokeWidth: 1,
                    dashArray: [3, 4],
                  ),
                if (range.length > 1)
                  HorizontalLine(
                    y: range[1],
                    color: const Color(0xFF82B89F),
                    strokeWidth: 1,
                    dashArray: [3, 4],
                  ),
              ]),
              titlesData: const FlTitlesData(
                topTitles:
                    AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    AxisTitles(sideTitles: SideTitles(showTitles: false)),
              ),
              lineBarsData: [
                LineChartBarData(
                  isCurved: true,
                  color: jalosGreen,
                  barWidth: 3,
                  dotData: FlDotData(
                    show: true,
                    getDotPainter: (spot, percent, barData, index) {
                      final isAnomaly = index < visibleSeries.length &&
                          visibleSeries[index].anomaly;
                      if (isAnomaly) {
                        return FlDotCirclePainter(
                          radius: 5,
                          color: const Color(0xFFE0533C),
                          strokeWidth: 2,
                          strokeColor: Colors.white,
                        );
                      }
                      return FlDotCirclePainter(
                        radius: 0,
                        color: Colors.transparent,
                      );
                    },
                  ),
                  belowBarData: BarAreaData(
                    show: true,
                    color: jalosGreen.withValues(alpha: 0.07),
                  ),
                  spots: [
                    for (int i = 0; i < visibleSeries.length; i++)
                      FlSpot(i.toDouble(), visibleSeries[i].litres)
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 12,
          runSpacing: 4,
          children: [
            _legend(jalosGreen, 'Household use'),
            _legend(const Color(0xFF8D86C5), 'Baseline (${baseline.round()} L)'),
            if (range.isNotEmpty)
              _legend(const Color(0xFF82B89F),
                  'Guidance (${range[0].round()}–${range.length > 1 ? range[1].round() : ''} L)'),
          ],
        ),
      ],
    );
  }

  Widget _legend(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 5),
        Text(
          label,
          style: const TextStyle(fontSize: 10, color: jalosMuted),
        ),
      ],
    );
  }
}
