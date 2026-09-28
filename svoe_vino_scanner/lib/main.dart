import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_svg/flutter_svg.dart';

void main() {
  runApp(const SvoeVinoApp());
}

class SvoeVinoApp extends StatelessWidget {
  const SvoeVinoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Своё Вино',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        scaffoldBackgroundColor: const Color(0xFFFEFDFA),
        primaryColor: const Color(0xFF8B3A3D),
        textTheme: GoogleFonts.interTextTheme(Theme.of(context).textTheme),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF8B3A3D),
            foregroundColor: Colors.white,
            elevation: 4,
            shadowColor: Colors.black.withOpacity(0.3),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
          ),
        ),
      ),
      home: const ScannerScreen(),
    );
  }
}

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  bool _isBottomSheetOpen = false;
  bool _isReverseSearch = false; // Переключатель реверсивного поиска

  final List<String> wineImages = [
    'assets/zakat_denisov_vajneri_no_bg_preview_carve_photos_1_6ae9baa13d.webp',
    'assets/Cantiani_Caber_Sauv_vid_042024_Photoroom_834a144a19.webp',
    'assets/CANTIANI_Igrist_Brut_vid5_042026_kopiya_1b13527c60.webp',
    'assets/CANTIANI_Igristoe_Riesl_vid_032025_kopiya_8150a5e627.webp',
    'assets/CANTIANI_Igristoe_Rkats_vid_032025_kopiya_29e44021af.webp',
    'assets/Cantiani_Reserve_1_e1bd881754.webp',
    'assets/MB_igrist_Blanc_vid_032026_kopiya_5c6680d1ef.webp',
    'assets/Gevyurcztraminer_Oranzh_Usadba_Petovskih_f3d914f332.webp',
    'assets/Image_ad611828e7.webp',
    'assets/petnat_muskat_no_bg_preview_carve_photos_2296dc8b1a.webp',
    'assets/priboj_Marchenko_beloe_no_bg_preview_carve_photos_de18758756.webp',
    'assets/Priboj_Marchenko_krasnoe_no_bg_preview_carve_photos_6e051269ba.webp',
    'assets/Priboj_Marchenko_rozovoe_no_bg_preview_carve_photos_a85f40aeb6.webp',
  ];

  void _showSommelierResult(BuildContext context) async {
    setState(() => _isBottomSheetOpen = true);

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.transparent,
      builder: (BuildContext context) {
        return const SommelierBottomSheet();
      },
    );

    setState(() => _isBottomSheetOpen = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          SingleChildScrollView(
            padding: const EdgeInsets.only(left: 16.0, right: 16.0, top: 110.0, bottom: 24.0),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 600),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Text(
                      'Свои вина',
                      style: GoogleFonts.playfairDisplay(fontSize: 42, color: const Color(0xFF1E293B)),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      _isReverseSearch
                          ? 'Сфотографируйте блюдо\nчтобы ИИ подобрал идеальное вино'
                          : 'Сфотографируйте этикетку Российского\nвина или загрузите фото, чтобы найти\nего',
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 16, color: Color(0xFF333333), height: 1.4),
                    ),
                    const SizedBox(height: 40),


                    Container(
                      padding: const EdgeInsets.all(32),
                      decoration: BoxDecoration(
                          color: const Color(0xFFFDF9ED),
                          borderRadius: BorderRadius.circular(24),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.03),
                              blurRadius: 15,
                              offset: const Offset(0, 5),
                            )
                          ]
                      ),
                      child: Column(
                        children: [

                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                  'Поиск вина',
                                  style: TextStyle(
                                      color: !_isReverseSearch ? const Color(0xFF1E293B) : Colors.grey,
                                      fontWeight: !_isReverseSearch ? FontWeight.w600 : FontWeight.normal
                                  )
                              ),
                              const SizedBox(width: 12),
                              GestureDetector(
                                onTap: () => setState(() => _isReverseSearch = !_isReverseSearch),
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 200),
                                  width: 50,
                                  height: 26,
                                  padding: const EdgeInsets.symmetric(horizontal: 2),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFD3AEAE), // Бледный бордовый фон
                                    borderRadius: BorderRadius.circular(13),
                                  ),
                                  alignment: _isReverseSearch ? Alignment.centerRight : Alignment.centerLeft,
                                  child: Container(
                                    width: 22,
                                    height: 22,
                                    decoration: const BoxDecoration(
                                      color: Color(0xFF8B3A3D),
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Text(
                                  'Подбор к блюду',
                                  style: TextStyle(
                                      color: _isReverseSearch ? const Color(0xFF8B3A3D) : Colors.grey,
                                      fontWeight: _isReverseSearch ? FontWeight.w600 : FontWeight.normal
                                  )
                              ),
                            ],
                          ),

                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 24.0),
                            child: SvgPicture.asset('assets/scanner.svg', height: 120),
                          ),
                          SizedBox(
                            width: double.infinity,
                            height: 52,
                            child: ElevatedButton(
                              onPressed: () => _showSommelierResult(context),
                              child: const Text('Сканировать', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                            ),
                          ),
                          const SizedBox(height: 16),
                          TextButton(
                            onPressed: () => _showSommelierResult(context),
                            child: const Text('Загрузить фото', style: TextStyle(fontSize: 16, color: Color(0xFF8B3A3D))),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 32),

                    OutlinedButton.icon(
                      onPressed: () {},
                      icon: const Icon(Icons.filter_list, color: Color(0xFF8B3A3D), size: 18),
                      label: const Text('Фильтр', style: TextStyle(color: Color(0xFF8B3A3D))),
                      style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Colors.grey, width: 0.5),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12)
                      ),
                    ),

                    const SizedBox(height: 32),

                    GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        crossAxisSpacing: 16,
                        mainAxisSpacing: 16,
                        childAspectRatio: 0.58,
                      ),
                      itemCount: 16,
                      itemBuilder: (context, index) {
                        return WineCardPlaceholder(
                          imagePath: wineImages[index % wineImages.length],
                        );
                      },
                    ),

                    const SizedBox(height: 32),

                    SizedBox(
                      width: double.infinity,
                      height: 52,
                      child: ElevatedButton(
                        onPressed: () {},
                        child: const Text('Показать ещё', style: TextStyle(fontSize: 16)),
                      ),
                    ),

                    const SizedBox(height: 24),

                    const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        _PaginationItem('1', isActive: true),
                        _PaginationItem('2'),
                        _PaginationItem('3'),
                        _PaginationItem('4'),
                        _PaginationItem('5'),
                        Padding(padding: EdgeInsets.symmetric(horizontal: 8), child: Text('...', style: TextStyle(color: Colors.grey))),
                        _PaginationItem('129'),
                      ],
                    ),
                    const SizedBox(height: 60),
                  ],
                ),
              ),
            ),
          ),

          Positioned(
            top: 24,
            left: 0,
            right: 0,
            child: Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 600),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(100),
                    child: BackdropFilter(
                      filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
                        decoration: const BoxDecoration(
                          color: Color(0x4DEFDBC6),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            SvgPicture.asset('assets/svoe-vino-logo.svg', height: 36),
                            Row(
                              children: [
                                const Icon(Icons.search, color: Color(0xFF8B3A3D), size: 28),
                                const SizedBox(width: 16),
                                Container(
                                  width: 64,
                                  height: 40,
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF8B3A3D),
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: const Icon(Icons.menu, color: Colors.white, size: 24),
                                ),
                              ],
                            )
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),

          IgnorePointer(
            ignoring: !_isBottomSheetOpen,
            child: TweenAnimationBuilder<double>(
              tween: Tween<double>(begin: 0.0, end: _isBottomSheetOpen ? 10.0 : 0.0),
              duration: const Duration(milliseconds: 350),
              builder: (context, blurValue, child) {
                if (blurValue == 0.0) return const SizedBox.shrink();
                return BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: blurValue, sigmaY: blurValue),
                  child: Container(
                    color: Colors.black.withOpacity(blurValue * 0.04),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class SommelierBottomSheet extends StatefulWidget {
  const SommelierBottomSheet({super.key});

  @override
  State<SommelierBottomSheet> createState() => _SommelierBottomSheetState();
}

class _SommelierBottomSheetState extends State<SommelierBottomSheet> {
  double _sheetPosition = 0.45;

  void _showRecipeDialog(BuildContext context, String product) {
    showDialog(
      context: context,
      builder: (BuildContext ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
          title: Row(
            children: [
              const Icon(Icons.restaurant_menu, color: Color(0xFF8B3A3D)),
              const SizedBox(width: 8),
              Text('Рецепт: $product', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 20)),
            ],
          ),
          content: Text(
            'ИИ-Сомелье рекомендует:\n\nИдеальное блюдо из категории "$product", которое подчеркнет ноты ежевики и перца в этом вине.',
            style: const TextStyle(fontSize: 16, height: 1.4),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Понятно', style: TextStyle(color: Color(0xFF8B3A3D), fontSize: 16)),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final isExpanded = _sheetPosition > 0.55;

    return NotificationListener<DraggableScrollableNotification>(
      onNotification: (notification) {
        setState(() {
          _sheetPosition = notification.extent;
        });
        return true;
      },
      child: DraggableScrollableSheet(
        initialChildSize: 0.45,
        minChildSize: 0.45,
        maxChildSize: 0.85,
        expand: false,
        builder: (_, controller) {
          return Stack(
            clipBehavior: Clip.none,
            children: [
              if (!isExpanded)
                Positioned(
                  top: -50,
                  left: 0,
                  right: 0,
                  child: AnimatedOpacity(
                    opacity: isExpanded ? 0.0 : 1.0,
                    duration: const Duration(milliseconds: 200),
                    child: const Column(
                      children: [
                        Icon(Icons.arrow_upward, color: Colors.white, size: 20),
                        SizedBox(height: 4),
                        Text('Потяните вверх', style: TextStyle(color: Colors.white, fontSize: 13)),
                      ],
                    ),
                  ),
                ),

              Container(
                decoration: const BoxDecoration(
                  color: Color(0xFFFDF9ED),
                  borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
                ),
                child: ListView(
                  controller: controller,
                  padding: const EdgeInsets.only(left: 24.0, right: 24.0, top: 24.0, bottom: 24.0),
                  children: [
                    Center(
                      child: Container(
                        width: 40, height: 4,
                        decoration: BoxDecoration(color: Colors.grey.shade400, borderRadius: BorderRadius.circular(10)),
                      ),
                    ),
                    const SizedBox(height: 24),

                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Image.asset('assets/zakat_denisov_vajneri_no_bg_preview_carve_photos_1_6ae9baa13d.webp', height: 160),
                        const SizedBox(width: 20),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(child: Text('Усадьба Дивноморское', style: GoogleFonts.playfairDisplay(fontSize: 24, fontWeight: FontWeight.bold, height: 1.1))),
                                  IconButton(
                                    icon: const Icon(Icons.ios_share, color: Color(0xFF8B3A3D)),
                                    onPressed: () {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(content: Text('Ссылка на карточку скопирована')),
                                      );
                                    },
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              const Text('Сира, 2020', style: TextStyle(fontSize: 16, color: Colors.grey)),
                              const SizedBox(height: 16),
                              Row(
                                children: [
                                  // Заменили эмодзи на иконку
                                  const Icon(Icons.star, color: Color(0xFF8B3A3D), size: 20),
                                  const SizedBox(width: 6),
                                  RichText(
                                    text: const TextSpan(
                                      style: TextStyle(color: Colors.black, fontSize: 16),
                                      children: [
                                        TextSpan(text: 'Рейтинг: '),
                                        TextSpan(text: '92', style: TextStyle(color: Color(0xFF8B3A3D), fontWeight: FontWeight.bold)),
                                        TextSpan(text: ' / 100', style: TextStyle(color: Colors.grey)),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        )
                      ],
                    ),
                    const SizedBox(height: 32),

                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                          color: const Color(0xFFF5EBE1),
                          borderRadius: BorderRadius.circular(16)
                      ),
                      child: const Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.auto_awesome, color: Color(0xFF8B3A3D)),
                          SizedBox(width: 12),
                          Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Факт от умного сомелье (ИИ)', style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF333333))),
                                  SizedBox(height: 8),
                                  Text('Вино выдерживалось в бочках из кавказского дуба, что придает ему ноты ежевики и черного перца.', style: TextStyle(height: 1.4)),
                                ],
                              )
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 32),

                    const Text('Идеально сочетается с:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
                    const SizedBox(height: 16),

                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.chevron_left, color: Color(0xFF8B3A3D), size: 28),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: [
                              // Теперь здесь графические Asset-иконки, а не системные шрифты
                              _GastroIcon('assets/meat.png', 'Мясо', onTap: () => _showRecipeDialog(context, 'Мясо')),
                              _GastroIcon('assets/cheese.png', 'Сыр', onTap: () => _showRecipeDialog(context, 'Сыр')),
                              _GastroIcon('assets/fruits.png', 'Фрукты', onTap: () => _showRecipeDialog(context, 'Фрукты')),
                              _GastroIcon('assets/bird.png', 'Птица', onTap: () => _showRecipeDialog(context, 'Птица')),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Icon(Icons.chevron_right, color: Color(0xFF8B3A3D), size: 28),
                      ],
                    ),
                    const SizedBox(height: 32),

                    Column(
                      children: [
                        SizedBox(
                          width: double.infinity,
                          height: 52,
                          child: ElevatedButton(
                            onPressed: () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Открывается карточка вина...')),
                              );
                            },
                            child: const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text('Перейти к карточке вина', style: TextStyle(fontSize: 16)),
                                SizedBox(width: 8),
                                Icon(Icons.arrow_forward, size: 18),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          height: 52,
                          child: OutlinedButton(
                            onPressed: () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Сканер для сравнения запущен')),
                              );
                            },
                            style: OutlinedButton.styleFrom(
                              side: const BorderSide(color: Color(0xFF8B3A3D), width: 1.5),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                            ),
                            child: const Text('Сравнить с другой бутылкой', style: TextStyle(fontSize: 16, color: Color(0xFF8B3A3D), fontWeight: FontWeight.bold)),
                          ),
                        ),
                      ],
                    )
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _PaginationItem extends StatelessWidget {
  final String number;
  final bool isActive;

  const _PaginationItem(this.number, {this.isActive = false});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 4),
      width: 40,
      height: 40,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: isActive ? Border.all(color: const Color(0xFF8B3A3D), width: 1.5) : null,
      ),
      child: Text(
        number,
        style: TextStyle(
            color: isActive ? const Color(0xFF8B3A3D) : Colors.black87,
            fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
            fontSize: 16
        ),
      ),
    );
  }
}

class _GastroIcon extends StatelessWidget {
  final String imagePath; // Изменено с IconData/Emoji на путь к картинке
  final String label;
  final VoidCallback onTap;

  const _GastroIcon(this.imagePath, this.label, {required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 54,
            height: 54,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFF8B3A3D), width: 1),
              color: Colors.transparent,
            ),
            // Отрисовка графического файла из assets (с защитой от ошибки, пока файлов нет)
            child: Padding(
              padding: const EdgeInsets.all(12.0),
              child: Image.asset(
                imagePath,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) => const Icon(Icons.fastfood, color: Color(0xFF8B3A3D), size: 24),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF333333))),
        ],
      ),
    );
  }
}

class WineCardPlaceholder extends StatelessWidget {
  final String imagePath;
  const WineCardPlaceholder({super.key, required this.imagePath});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFFDF9ED),
        borderRadius: BorderRadius.circular(24),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Center(
              child: Image.asset(
                imagePath,
                fit: BoxFit.contain,
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text('Название вина', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)), maxLines: 1, overflow: TextOverflow.ellipsis),
          const SizedBox(height: 4),
          Text('Производитель', style: TextStyle(fontSize: 12, color: Colors.grey.shade500), maxLines: 1, overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}