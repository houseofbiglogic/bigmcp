=========
Changelog
=========

19.0.1.0.2 (2026-10-02)
=======================

- ``call_method`` artık çağıran kullanıcının bağlamını (dil, saat dilimi, seçili
  şirketler) korur. Önceden çağrıya bir ``context`` verildiğinde — okuma
  metotlarında ise her zaman — bu bağlam tümüyle eziliyor, sonuçlar kullanıcının
  dili ve şirketleri yerine varsayılanlarla dönüyordu. Çağrıda verilen
  ``context`` anahtarları yine önceliklidir.

19.0.1.0.1 (2026-10-02)
=======================

- **Ayarlar > Genel Ayarlar > Entegrasyonlar** bölümüne **MCP Result Limit
  (tokens)** ayarı eklendi: tek bir araç çağrısının asistana döndürebileceği en
  büyük sonuç (varsayılan 25.000 token, 1 token ≈ 3 karakter). Sınırı aşan
  sonuç kesilir ve asistana isteği nasıl daraltacağı (daha az alan / daha az
  kayıt) bildirilir. Modül artık ``base_setup``'a bağımlıdır.
- ``search_read`` artık ``{total, records}`` döndürür: ``total`` domain'e uyan
  tüm kayıtların sayısıdır, böylece asistan ``limit`` ile kesilmiş bir sayfayı
  tam sonuçtan ayırt eder. Yeni ``context`` parametresi ile dil seçilebilir ya
  da ``{'active_test': false}`` ile arşivlenmiş kayıtlar dahil edilebilir.
- ``list_models`` artık kullanıcının okuyabildiği **tüm** modelleri, tanımlayan
  modüle göre gruplayarak döndürür (``{modül: {model: etiket}}``); ``limit``
  parametresi kaldırıldı, yerine ``module`` filtresi geldi.
- ``describe_model`` genel görünümde alanların yardım metinlerini göndermez;
  yeni ``fields`` parametresiyle adı verilen alanlar yardım metniyle birlikte
  açıklanır. Domain'de filtrelenemeyen, sıralanamayan ve gruplanamayan alanlar
  ``searchable=false`` ile işaretlenir. ``web_read``, ``get_views`` gibi her
  modelde bulunan genel metotlar yalnızca ``include_orm_methods`` ile listelenir.
- Binary alanlar okumalarda içerik yerine boyut olarak döner (``search_read``
  ve ``call_method`` ile çağrılan salt-okunur metotlar); base64 içerik için
  context'e ``{'bin_size': false}`` verilir.
- Asistan talimatları güncellendi: sayım, toplam ve sıralamalar için
  ``search_read`` satırlarını toplamak yerine ``search_count`` veya
  ``formatted_read_group`` kullanılması yönlendirilir (``read_group`` yerine).
- Araç sonuçları boşluksuz (kompakt) JSON olarak gönderilir; aynı veri daha az
  token harcar.

