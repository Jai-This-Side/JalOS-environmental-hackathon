import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import '../../core/constants.dart';
import '../../models/complaint_item.dart';
import '../../providers/app_providers.dart';
import '../../widgets/metric_card.dart';

class ComplaintsTab extends ConsumerWidget {
  const ComplaintsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final complaints = ref.watch(complaintsProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(complaintsProvider.notifier).refresh();
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 80),
          children: [
            const Text(
              'Water Complaints',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w800,
                color: jalosInk,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 2),
            const Text(
              'Report society water issues and track maintenance progress',
              style: TextStyle(color: jalosMuted, fontSize: 12),
            ),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () => _openCreateModal(context, ref),
                icon: const Icon(Icons.add_rounded, size: 20),
                label: const Text('Report New Issue'),
                style: FilledButton.styleFrom(
                  backgroundColor: jalosGreen,
                  padding: const EdgeInsets.symmetric(vertical: 13),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 14),
            if (complaints.isEmpty)
              metricCard(
                child: const Center(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 24),
                    child: Column(
                      children: [
                        Icon(Icons.check_circle_outline_rounded,
                            color: jalosGreen, size: 36),
                        SizedBox(height: 8),
                        Text(
                          'No open complaints',
                          style: TextStyle(
                            fontWeight: FontWeight.w700,
                            color: jalosInk,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'All water services are operating normally.',
                          style: TextStyle(fontSize: 12, color: jalosMuted),
                        ),
                      ],
                    ),
                  ),
                ),
              )
            else
              ...complaints.map((c) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _complaintCard(context, ref, c),
                  )),
          ],
        ),
      ),
    );
  }

  Widget _complaintCard(
      BuildContext context, WidgetRef ref, ComplaintItem item) {
    final statusColor = item.status == 'RESOLVED' || item.status == 'CLOSED'
        ? jalosNormalText
        : item.status == 'IN_PROGRESS'
            ? jalosModerateText
            : const Color(0xFF5A7267);

    final statusBg = item.status == 'RESOLVED' || item.status == 'CLOSED'
        ? jalosNormalBg
        : item.status == 'IN_PROGRESS'
            ? jalosModerateBg
            : const Color(0xFFEFF5F2);

    return metricCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  item.title,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 14,
                    color: jalosInk,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: statusBg,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  item.status,
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                    color: statusColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            item.description,
            style: const TextStyle(fontSize: 12, color: Color(0xFF556960)),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Text(
                '${item.category} · ${item.createdAt}',
                style: const TextStyle(fontSize: 10, color: jalosMuted),
              ),
              const Spacer(),
              if (item.photoUrl != null)
                TextButton.icon(
                  onPressed: () => _viewPhoto(context, ref, item.id),
                  icon: const Icon(Icons.image_outlined, size: 16),
                  label: const Text('View Photo',
                      style: TextStyle(fontSize: 11)),
                  style: TextButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                    foregroundColor: jalosGreen,
                  ),
                ),
            ],
          ),
          if (item.updates.isNotEmpty) ...[
            const Divider(height: 16, color: Color(0xFFF0F4F2)),
            const Text(
              'Admin Updates',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: jalosInk,
              ),
            ),
            const SizedBox(height: 4),
            ...item.updates.map((u) => Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.reply_rounded,
                          size: 14, color: jalosGreen),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          '${u.status}: ${u.comment}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: Color(0xFF386354),
                          ),
                        ),
                      ),
                    ],
                  ),
                )),
          ],
        ],
      ),
    );
  }

  Future<void> _viewPhoto(
      BuildContext context, WidgetRef ref, int complaintId) async {
    try {
      final api = ref.read(apiServiceProvider);
      final bytes = await api.getComplaintPhoto(complaintId);
      if (!context.mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Attached Photo',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          content: ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 380),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.memory(bytes, fit: BoxFit.contain),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not load complaint photo.')),
        );
      }
    }
  }

  Future<void> _openCreateModal(BuildContext context, WidgetRef ref) async {
    final title = TextEditingController();
    final description = TextEditingController();
    final picker = ImagePicker();
    XFile? selectedPhoto;
    String category = 'WATER_NOT_AVAILABLE';
    bool submitting = false;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (sheetContext) => StatefulBuilder(
        builder: (sheetContext, setModalState) => Padding(
          padding: EdgeInsets.fromLTRB(20, 8, 20,
              MediaQuery.of(sheetContext).viewInsets.bottom + 20),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Report Water Issue',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    color: jalosInk,
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: category,
                  decoration: const InputDecoration(
                    labelText: 'Issue Category',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(
                        value: 'WATER_NOT_AVAILABLE',
                        child: Text('Water not available')),
                    DropdownMenuItem(
                        value: 'LOW_PRESSURE', child: Text('Low pressure')),
                    DropdownMenuItem(
                        value: 'WATER_QUALITY',
                        child: Text('Water quality / contamination')),
                    DropdownMenuItem(
                        value: 'LEAKAGE', child: Text('Visible pipe leakage')),
                    DropdownMenuItem(
                        value: 'SUPPLY_DELAY',
                        child: Text('Supply or tanker delay')),
                    DropdownMenuItem(
                        value: 'TANK_ISSUE', child: Text('Tank cleaning / issue')),
                    DropdownMenuItem(value: 'OTHER', child: Text('Other')),
                  ],
                  onChanged: (val) {
                    if (val != null) setModalState(() => category = val);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: title,
                  decoration: const InputDecoration(
                    labelText: 'Summary / Title',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: description,
                  minLines: 3,
                  maxLines: 5,
                  decoration: const InputDecoration(
                    labelText: 'Detailed Description',
                    hintText: 'Describe location, floor, and symptom…',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 10,
                  runSpacing: 8,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () async {
                        try {
                          final photo = await picker.pickImage(
                            source: ImageSource.camera,
                            maxWidth: 1600,
                            maxHeight: 1600,
                            imageQuality: 82,
                          );
                          if (photo != null) {
                            setModalState(() => selectedPhoto = photo);
                          }
                        } catch (_) {}
                      },
                      icon: const Icon(Icons.camera_alt_outlined, size: 18),
                      label: const Text('Take Photo'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () async {
                        try {
                          final photo = await picker.pickImage(
                            source: ImageSource.gallery,
                            maxWidth: 1600,
                            maxHeight: 1600,
                            imageQuality: 82,
                          );
                          if (photo != null) {
                            setModalState(() => selectedPhoto = photo);
                          }
                        } catch (_) {}
                      },
                      icon: const Icon(Icons.photo_library_outlined, size: 18),
                      label: const Text('Upload Photo'),
                    ),
                    if (selectedPhoto != null)
                      TextButton.icon(
                        onPressed: () =>
                            setModalState(() => selectedPhoto = null),
                        icon: const Icon(Icons.close, size: 16),
                        label: const Text('Remove'),
                      ),
                  ],
                ),
                if (selectedPhoto != null) ...[
                  const SizedBox(height: 10),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.file(
                      File(selectedPhoto!.path),
                      height: 120,
                      width: double.infinity,
                      fit: BoxFit.cover,
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: submitting
                        ? null
                        : () async {
                            final t = title.text.trim();
                            final d = description.text.trim();
                            if (t.isEmpty || d.isEmpty) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                    content: Text('Please fill all fields.')),
                              );
                              return;
                            }
                            setModalState(() => submitting = true);
                            try {
                              await ref
                                  .read(complaintsProvider.notifier)
                                  .createComplaint(
                                    category: category,
                                    title: t,
                                    description: d,
                                    photo: selectedPhoto != null
                                        ? File(selectedPhoto!.path)
                                        : null,
                                  );
                              if (sheetContext.mounted) {
                                Navigator.pop(sheetContext);
                              }
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                      content: Text('Complaint registered successfully.')),
                                );
                              }
                            } catch (_) {
                              setModalState(() => submitting = false);
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                      content: Text(
                                          'Failed to submit complaint. Try again.')),
                                );
                              }
                            }
                          },
                    style: FilledButton.styleFrom(
                      backgroundColor: jalosGreen,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: Text(
                        submitting ? 'Submitting…' : 'Submit Water Complaint'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    title.dispose();
    description.dispose();
  }
}
