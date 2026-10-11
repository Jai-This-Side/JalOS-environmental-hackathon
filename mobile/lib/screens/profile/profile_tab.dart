import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants.dart';
import '../../providers/app_providers.dart';
import '../../widgets/metric_card.dart';

class ProfileTab extends ConsumerWidget {
  const ProfileTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final user = auth.user;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
      children: [
        const Text(
          'Your Household Profile',
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.w800,
            color: jalosInk,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 2),
        const Text(
          'Account credentials and household access configuration',
          style: TextStyle(
            color: jalosMuted,
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 14),

        metricCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'ACCOUNT',
                style: TextStyle(
                  fontSize: 10,
                  letterSpacing: 0.8,
                  fontWeight: FontWeight.w700,
                  color: jalosMuted,
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  CircleAvatar(
                    radius: 22,
                    backgroundColor: jalosMint,
                    child: const Icon(
                      Icons.person,
                      color: jalosGreen,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user?.email ?? 'resident@jalos.local',
                          style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 14,
                            color: jalosInk,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${user?.tower ?? 'Tower C'} · Flat ${user?.flatNumber ?? 'C-101'}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: jalosGreen,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              const Divider(
                height: 1,
                color: Color(0xFFF0F4F2),
              ),
              const SizedBox(height: 10),
              const Row(
                children: [
                  Icon(
                    Icons.lock_person_outlined,
                    color: jalosGreen,
                    size: 16,
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Your meter telemetry is private. Other society residents cannot see your consumption.',
                      style: TextStyle(
                        fontSize: 11,
                        color: jalosMuted,
                      ),
                    ),
                  ),
                ],
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
                'Security',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 14,
                  color: jalosInk,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Protect your household access with a strong password.',
                style: TextStyle(
                  fontSize: 11,
                  color: jalosMuted,
                ),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: () => _changePasswordModal(context, ref),
                icon: const Icon(
                  Icons.password_rounded,
                  size: 18,
                ),
                label: const Text('Change Password'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: jalosInk,
                  side: const BorderSide(
                    color: Color(0xFFD4E0DB),
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
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
                'System Environment',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 14,
                  color: jalosInk,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'API Endpoint: $apiBase',
                style: TextStyle(
                  fontSize: 11,
                  color: jalosMuted,
                ),
              ),
              const SizedBox(height: 2),
              const Text(
                'WebSocket: $socketBase',
                style: TextStyle(
                  fontSize: 11,
                  color: jalosMuted,
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () {
                    ref.read(authProvider.notifier).logout();
                  },
                  icon: const Icon(
                    Icons.logout_rounded,
                    size: 18,
                    color: jalosCriticalText,
                  ),
                  label: const Text(
                    'Sign Out of JalOS',
                    style: TextStyle(
                      color: jalosCriticalText,
                    ),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(
                      color: Color(0xFFFFD5CE),
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _changePasswordModal(
    BuildContext context,
    WidgetRef ref,
  ) async {
    final result = await showDialog<_PasswordChangeValues>(
      context: context,
      barrierDismissible: true,
      builder: (_) => const _ChangePasswordDialog(),
    );

    // User pressed Cancel / dismissed the dialog.
    if (!context.mounted || result == null) {
      return;
    }

    try {
      final api = ref.read(apiServiceProvider);

      await api.changePassword(
        result.currentPassword,
        result.newPassword,
      );

      if (!context.mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Password updated successfully.'),
        ),
      );
    } catch (_) {
      if (!context.mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Could not change password. Check current password.',
          ),
        ),
      );
    }
  }
}

/// Value returned by the password dialog when the user
/// successfully submits the form.
class _PasswordChangeValues {
  final String currentPassword;
  final String newPassword;

  const _PasswordChangeValues({
    required this.currentPassword,
    required this.newPassword,
  });
}

/// Owns its TextEditingControllers and disposes them correctly.
class _ChangePasswordDialog extends StatefulWidget {
  const _ChangePasswordDialog();

  @override
  State<_ChangePasswordDialog> createState() =>
      _ChangePasswordDialogState();
}

class _ChangePasswordDialogState
    extends State<_ChangePasswordDialog> {
  final _formKey = GlobalKey<FormState>();

  late final TextEditingController _currentController;
  late final TextEditingController _newController;
  late final TextEditingController _confirmController;

  @override
  void initState() {
    super.initState();

    _currentController = TextEditingController();
    _newController = TextEditingController();
    _confirmController = TextEditingController();
  }

  @override
  void dispose() {
    _currentController.dispose();
    _newController.dispose();
    _confirmController.dispose();

    super.dispose();
  }

  void _cancel() {
    Navigator.of(context).pop();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    Navigator.of(context).pop(
      _PasswordChangeValues(
        currentPassword: _currentController.text,
        newPassword: _newController.text,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text(
        'Change Password',
        style: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w800,
        ),
      ),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _currentController,
                obscureText: true,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: 'Current password',
                ),
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Enter current password';
                  }

                  return null;
                },
              ),

              TextFormField(
                controller: _newController,
                obscureText: true,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: 'New password (min 12 chars)',
                ),
                validator: (value) {
                  if (value == null || value.length < 12) {
                    return 'Use at least 12 characters';
                  }

                  return null;
                },
              ),

              TextFormField(
                controller: _confirmController,
                obscureText: true,
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => _submit(),
                decoration: const InputDecoration(
                  labelText: 'Confirm new password',
                ),
                validator: (value) {
                  if (value != _newController.text) {
                    return 'Passwords do not match';
                  }

                  return null;
                },
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _cancel,
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _submit,
          style: FilledButton.styleFrom(
            backgroundColor: jalosGreen,
          ),
          child: const Text('Update Password'),
        ),
      ],
    );
  }
}