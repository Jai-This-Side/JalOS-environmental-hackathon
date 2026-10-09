import 'package:flutter/material.dart';

class AnimatedTank extends StatefulWidget {
  final double level;
  final String risk;

  const AnimatedTank({
    super.key,
    required this.level,
    this.risk = 'NORMAL',
  });

  @override
  State<AnimatedTank> createState() => _AnimatedTankState();
}

class _AnimatedTankState extends State<AnimatedTank>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..value = (widget.level / 100).clamp(0.0, 1.0);
  }

  @override
  void didUpdateWidget(covariant AnimatedTank oldWidget) {
    super.didUpdateWidget(oldWidget);
    final target = (widget.level / 100).clamp(0.0, 1.0);
    if (target != _controller.value) {
      _controller.animateTo(target, curve: Curves.easeInOutCubic);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  List<Color> get _waterGradient {
    final level = widget.level;
    final risk = widget.risk.toUpperCase();

    if (risk == 'CRITICAL' || level <= 20) {
      return const [Color(0xFFE0533C), Color(0xFFC0392B)];
    } else if (risk == 'HIGH' || risk == 'MODERATE' || level <= 45) {
      return const [Color(0xFFE6A23C), Color(0xFFD35400)];
    } else {
      return const [Color(0xFF68C6B2), Color(0xFF218F82)];
    }
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 140,
      height: 154,
      child: Stack(
        alignment: Alignment.topCenter,
        children: [
          Positioned(
            top: 14,
            bottom: 4,
            child: Container(
              width: 104,
              decoration: BoxDecoration(
                color: const Color(0xFFEAF5F2),
                border: Border.all(color: const Color(0xFF91BEB1), width: 2),
                borderRadius: BorderRadius.circular(22),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x14225449),
                    blurRadius: 12,
                    offset: Offset(0, 5),
                  )
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(19),
                child: Stack(
                  alignment: Alignment.bottomCenter,
                  children: [
                    AnimatedBuilder(
                      animation: _controller,
                      builder: (context, child) => FractionallySizedBox(
                        heightFactor: _controller.value,
                        widthFactor: 1,
                        alignment: Alignment.bottomCenter,
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: _waterGradient,
                            ),
                          ),
                          child: child,
                        ),
                      ),
                      child: const Align(
                        alignment: Alignment.topCenter,
                        child: Padding(
                          padding: EdgeInsets.only(top: 2),
                          child: Divider(
                            height: 2,
                            thickness: 2,
                            color: Color(0xAAE8FFFA),
                          ),
                        ),
                      ),
                    ),
                    Positioned.fill(
                      child: IgnorePointer(
                        child: CustomPaint(painter: _TankScalePainter()),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            top: 6,
            child: Container(
              width: 114,
              height: 11,
              decoration: BoxDecoration(
                color: const Color(0xFFB7D8CE),
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TankScalePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0x6690B9AE)
      ..strokeWidth = 1.2;
    for (var tick = 1; tick <= 3; tick++) {
      final y = size.height * tick / 4;
      canvas.drawLine(
        Offset(size.width - 15, y),
        Offset(size.width - 4, y),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
