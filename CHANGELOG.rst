=========
Changelog
=========

19.0.2.0.1 (2026-10-20)
=======================

- Çeviri altyapısı: ``i18n/bigmcp.pot`` şablonu ve **Türkçe** çeviri
  (``i18n/tr.po``, 39 terimin tamamı). Grup adları, MCP notu alanları ve
  ayar etiketleri Odoo Türkçe kullanıldığında çevrilmiş görünür.
- README artık iki dilli: ana ``README.rst`` İngilizce, Türkçe metin
  ``README.tr.rst``; her ikisinin başında dil bağlantısı. Manifestteki
  açıklama kaldırıldı, Uygulamalar sayfasındaki modül açıklaması da
  ``README.rst``'den gelir.

19.0.2.0.0 (2026-10-20)
=======================

- **MCP 2026-07-28 desteği.** Sunucu artık çift çağlı: aynı ``/mcp`` adresi hem
  el sıkışmasız modern istemcilere (her istekte ``_meta`` ile sürüm ve
  yetenekler, yeni ``server/discover`` çağrısı, sonuçlarda ``resultType`` ve
  sunucu kimliği, zorunlu ``MCP-Protocol-Version`` / ``Mcp-Method`` /
  ``Mcp-Name`` başlıklarının gövdeyle doğrulanması, desteklenmeyen sürümde
  ``supported`` listesiyle ``-32022`` hatası, bilinmeyen metotta ``404``)
  hem de ``initialize`` ile açan eski istemcilere (2025-11-25, 2025-06-18,
  2025-03-26; istenen sürüm geri bildirilir) hizmet verir. Modern mesaj
  içeren toplu (batch) istekler reddedilir.
- Ayarlar artık Ayarlar sayfasında modülün ikonuyla kendi **BigMCP** başlığı
  altında (yalnızca **MCP Admin** görür); ``base_setup`` bağımlılığı kalktı.
  İki yeni ayar:

  - **MCP Cache Duration (minutes)** — modern istemcilerin araç listesini ve
    sunucu talimatlarını (genel notlar) yeniden sormadan kullanabileceği
    süre; varsayılan 10 dakika.
  - **MCP Allowed Origins** — tarayıcıdan gelen isteklerde kabul edilen
    siteler. Varsayılan ``*`` (hepsi); virgülle ayrılmış liste girilirse
    yalnızca listedekiler ve Odoo'nun kendi adresi kabul edilir, diğerleri
    ``403`` alır. Sunucudan sunucuya bağlantılar etkilenmez.
- MCP el sıkışmasında bildirilen sunucu sürümü artık manifestten okunur.
- Son kullanıcı için adım adım kurulum kılavuzu (``README.rst``): kurulum,
  yetki ve API anahtarı, istemci bağlantısı, ayarlar, MCP notları örneklerle,
  güvenlik ve sorun giderme.
- Modül ikonu eklendi; ``LICENSE`` dosyası manifestle uyumlu olarak LGPL-3
  metnine çevrildi; ``.gitignore`` artık ``*.pot`` dosyalarını dışlamıyor.

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


19.0.1.0.0 (2026-09-17)
=======================

- İlk yayın: ``POST /mcp`` adresinde durumsuz MCP (Streamable HTTP, JSON-RPC
  2.0) uç noktası; ``list_models``, ``describe_model``, ``describe_method``,
  ``search_read`` ve ``call_method`` araçları; API anahtarıyla (Bearer)
  kimlik doğrulama ve **MCP User** / **MCP Admin** rolleri; asistana genel,
  model ya da metot düzeyinde gösterilen **MCP Notes**.
