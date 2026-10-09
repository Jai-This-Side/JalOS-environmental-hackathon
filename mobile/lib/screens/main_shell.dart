import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/constants.dart';
import '../providers/app_providers.dart';
import 'alerts/alerts_tab.dart';
import 'complaints/complaints_tab.dart';
import 'home/home_tab.dart';
import 'profile/profile_tab.dart';
import 'usage/usage_tab.dart';
import 'water/water_tab.dart';

class MainShell extends ConsumerStatefulWidget {
  const MainShell({super.key});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  int currentTab = 0;

  final pages = const [
    HomeTab(),
    UsageTab(),
    WaterTab(),
    ComplaintsTab(),
    AlertsTab(),
    ProfileTab(),
  ];

  @override
  Widget build(BuildContext context) {
    final alerts = ref.watch(alertsProvider);
    final unreadAlerts = alerts.where((a) => !a.read).length;

    return Scaffold(
      backgroundColor: jalosBg,
      appBar: AppBar(
        backgroundColor: jalosBg,
        elevation: 0,
        title: const Row(
          children: [
            Icon(Icons.water_drop_rounded, color: jalosGreen, size: 22),
            SizedBox(width: 8),
            Text(
              'jalos',
              style: TextStyle(
                fontWeight: FontWeight.w900,
                color: jalosInk,
                letterSpacing: -1,
                fontSize: 22,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh Telemetry',
            icon: const Icon(Icons.refresh_rounded, color: jalosInk),
            onPressed: () {
              ref.read(waterStatusProvider.notifier).refresh();
              ref.read(usageProvider.notifier).refresh();
              ref.read(alertsProvider.notifier).refresh();
            },
          ),
          IconButton(
            tooltip: 'Sign Out',
            icon: const Icon(Icons.logout_rounded, color: jalosInk),
            onPressed: () {
              ref.read(authProvider.notifier).logout();
            },
          ),
        ],
      ),
      body: IndexedStack(
        index: currentTab,
        children: pages,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentTab,
        onDestinationSelected: (idx) => setState(() => currentTab = idx),
        destinations: [
          const NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Home',
          ),
          const NavigationDestination(
            icon: Icon(Icons.bar_chart_rounded),
            label: 'Usage',
          ),
          const NavigationDestination(
            icon: Icon(Icons.water_drop_outlined),
            selectedIcon: Icon(Icons.water_drop),
            label: 'Water',
          ),
          const NavigationDestination(
            icon: Icon(Icons.report_problem_outlined),
            selectedIcon: Icon(Icons.report_problem),
            label: 'Complaints',
          ),
          NavigationDestination(
            icon: unreadAlerts == 0
                ? const Icon(Icons.notifications_none_rounded)
                : Badge(
                    label: Text('$unreadAlerts'),
                    child: const Icon(Icons.notifications_none_rounded),
                  ),
            selectedIcon: unreadAlerts == 0
                ? const Icon(Icons.notifications)
                : Badge(
                    label: Text('$unreadAlerts'),
                    child: const Icon(Icons.notifications),
                  ),
            label: 'Alerts',
          ),
          const NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
