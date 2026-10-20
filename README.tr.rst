==========================
BigMCP — Odoo MCP Sunucusu
==========================

`English <README.rst>`_ | **Türkçe**

    Odoo'nuzu Claude gibi yapay zekâ asistanlarına açan köprü. Asistan,
    Odoo'daki modelleri ve alanları kendisi keşfeder; kayıtları arar, okur ve
    — izin verdiğiniz ölçüde — oluşturur ya da günceller. Her işlem, bağlanan
    kullanıcının **kendi Odoo yetkileriyle** yapılır: kullanıcı neyi
    göremiyorsa asistan da göremez.

- **Teknik adı:** ``bigmcp``
- **Versiyon:** ``19.0.2.0.1`` (Odoo 19)
- **Bağımlılıklar:** ``api_doc`` (Odoo ile gelir)
- **Lisans:** LGPL-3
- **Yazar:** BigLogic — https://biglogic.tech

.. contents::
   :local:
   :depth: 2

----

1. MCP Nedir, Bu Modül Ne Yapar?
================================

**MCP (Model Context Protocol)**, yapay zekâ asistanlarının dış sistemlere
bağlanmasını sağlayan ortak bir dildir. Nasıl bir yazıcı sürücüsü sayesinde her
program aynı yazıcıya yazdırabiliyorsa, MCP sayesinde de Claude Desktop, Claude
Code ya da MCP destekleyen başka bir asistan aynı Odoo'ya bağlanabilir.

BigMCP, Odoo'nuzun ``/mcp`` adresinde böyle bir bağlantı noktası açar. Asistan
bağlandığında beş genel araç görür:

===================  ==========================================================
Araç                 Ne yapar?
===================  ==========================================================
``list_models``      Kullanıcının görebildiği modelleri (Müşteri, Satış
                     Siparişi, Fatura…) modüle göre gruplayarak listeler.
``describe_model``   Bir modelin alanlarını, metotlarını ve o modele yazılmış
                     MCP notlarını gösterir.
``describe_method``  Tek bir metodun ne yaptığını ve parametrelerini açıklar.
``search_read``      Kayıt arar ve okur (toplam sayı + bir sayfa kayıt).
``call_method``      Bir metodu çağırır: kayıt oluşturma, güncelleme, silme,
                     sipariş onaylama gibi **veri değiştiren** işlemler.
===================  ==========================================================

Böylece asistana "Bu ay İstanbul'daki müşterilere kesilen faturaların toplamı
ne?" diye sorduğunuzda asistan önce fatura modelini bulur, alanlarını inceler,
sonra doğru sorguyu kendisi kurar. Her iş akışı için ayrı bir araç yazılması
gerekmez.

Sizin yapacağınız üç şey var:

1. Modülü kurmak ve kullanıcılara **MCP yetkisi** vermek.
2. Her kullanıcı için bir **API anahtarı** üretip asistana tanıtmak.
3. (İsteğe bağlı ama önerilir) **MCP notları** ile asistana şirketinize özgü
   kuralları öğretmek (bkz. bölüm 5).

----

2. Kurulum
==========

2.1 Ön koşullar
---------------

- Odoo 19.
- Odoo'nun, asistanın çalıştığı yerden erişilebilir bir adresi
  (ör. ``https://odoo.sirketiniz.com``). Claude.ai gibi bulut asistanları için
  bu adres internetten ulaşılabilir olmalıdır; Claude Desktop ya da Claude Code
  ile kendi ağınızdaki bir Odoo'ya da bağlanabilirsiniz.
- **HTTPS** şiddetle önerilir: API anahtarı her istekte gönderilir.

2.2 Modülü kurma
----------------

1. ``bigmcp`` klasörünü Odoo'nun addons yoluna kopyalayın.
2. Odoo sunucusunu yeniden başlatın.
3. Geliştirici modunu açın (**Ayarlar > Geliştirici Araçlarını Etkinleştir**)
   ve **Uygulamalar > Uygulama Listesini Güncelle**'ye tıklayın.
4. Uygulamalar'da **BigMCP** araması yapıp **Kur**'a basın.

Kurulumla birlikte ``api_doc`` modülü de (Odoo'nun kendi API dokümantasyon
modülü) otomatik olarak etkinleşir.

2.3 Kullanıcıya MCP yetkisi verme
---------------------------------

Asistanla bağlanacak her kullanıcıya MCP rolü verilmelidir; rolü olmayan bir
kullanıcı geçerli bir anahtarla bile bağlanamaz.

1. **Ayarlar > Kullanıcılar ve Şirketler > Kullanıcılar**'ı açın.
2. Kullanıcı formunda **MCP Server** başlığı altındaki **MCP Role** alanını
   seçin:

   ===============  ==============================================================
   Rol              Yetki
   ===============  ==============================================================
   *(boş)*          MCP üzerinden bağlanamaz.
   **MCP User**     ``/mcp`` adresine API anahtarıyla bağlanabilir. Odoo
                    erişim hakları her çağrıda aynen uygulanır.
   **MCP Admin**    MCP User'ın yapabildiklerine ek olarak **MCP notlarını**
                    yazıp düzenleyebilir.
   ===============  ==============================================================

3. Kaydedin.

**Ayarlar** uygulamasına tam erişimi olan yöneticiler otomatik olarak
**MCP Admin** olur; onlar için ek bir işlem gerekmez.

.. note::

   MCP yetkisi, kullanıcıya yeni bir veri erişimi **vermez**. Kullanıcı Odoo
   arayüzünde hangi kayıtları görüp düzenleyebiliyorsa asistan da tam olarak
   onları görüp düzenleyebilir. Bu yüzden asistana geniş yetkili bir yönetici
   hesabı yerine, gerçekten ihtiyaç duyulan yetkilere sahip bir kullanıcı
   hesabı bağlamak en güvenli yoldur.

2.4 API anahtarı üretme
-----------------------

API anahtarı, asistanın Odoo'ya "ben bu kullanıcıyım" demesini sağlayan bir
şifredir. Her kullanıcı kendi anahtarını kendi profilinden üretir:

1. Sağ üstteki kullanıcı adınıza tıklayıp **Tercihler** (*My Profile*)'i açın.
2. **Güvenlik** (*Security*) sekmesine geçin.
3. **API Anahtarı Ekle** (*Add API Key*) düğmesine basın; Odoo önce şifrenizi
   yeniden sorar.
4. Bir **açıklama** yazın (ör. ``Claude Desktop``) ve bir **süre** seçin.
   Süre dolunca anahtar kendiliğinden geçersiz olur; yeni anahtar üretmeniz
   yeterlidir. Süresiz anahtarı yalnızca yöneticiler oluşturabilir.
5. Odoo anahtarı **yalnızca bir kez** gösterir. Kopyalayıp güvenli bir yerde
   saklayın; pencereyi kapattıktan sonra bir daha görüntülenemez.

Anahtarı kaybederseniz ya da ele geçirildiğinden şüphelenirseniz aynı ekrandan
silip yenisini üretin.

.. warning::

   API anahtarı, şifreniz kadar değerlidir. E-posta ya da sohbetle
   paylaşmayın; yalnızca bağlanacağınız asistanın ayarına yazın.

2.5 Asistanı Odoo'ya bağlama
----------------------------

Asistana üç bilgi verilir:

=================  ============================================================
Bilgi              Değer
=================  ============================================================
Sunucu adresi      ``https://odoo.sirketiniz.com/mcp``
Bağlantı türü      Streamable HTTP (bazı istemciler sadece "HTTP" der)
Kimlik doğrulama   ``Authorization: Bearer <API anahtarınız>`` başlığı
=================  ============================================================

**Claude Code** (terminal) için tek komut yeterlidir::

    claude mcp add --transport http odoo https://odoo.sirketiniz.com/mcp \
        --header "Authorization: Bearer BURAYA_API_ANAHTARI"

**Claude Desktop** için ``claude_desktop_config.json`` dosyasına aşağıdaki
bloğu ekleyin (Ayarlar > Geliştirici > Yapılandırmayı Düzenle). Bilgisayarda
Node.js kurulu olmalıdır::

    {
      "mcpServers": {
        "odoo": {
          "command": "npx",
          "args": [
            "-y", "mcp-remote",
            "https://odoo.sirketiniz.com/mcp",
            "--header", "Authorization:${ODOO_AUTH}"
          ],
          "env": {
            "ODOO_AUTH": "Bearer BURAYA_API_ANAHTARI"
          }
        }
      }
    }

Dosyayı kaydedip Claude Desktop'ı tamamen kapatıp açın. Sohbet ekranındaki
araçlar menüsünde ``odoo`` adlı bir sunucu ve beş araç görünmelidir.

Başka bir MCP istemcisi kullanıyorsanız yukarıdaki üç bilgiyi o istemcinin
"uzak MCP sunucusu" ekranına girin. İstemcinin özel bir **Authorization**
başlığı gönderebilmesi gerekir; yalnızca OAuth destekleyen istemciler BigMCP'ye
doğrudan bağlanamaz.

2.6 Bağlantıyı test etme
------------------------

Asistanı kurmadan önce bağlantıyı denemek isterseniz, bir terminalden::

    curl -X POST https://odoo.sirketiniz.com/mcp \
      -H "Authorization: Bearer BURAYA_API_ANAHTARI" \
      -H "Content-Type: application/json" \
      -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'

Her şey yolundaysa yanıt ``{"jsonrpc": "2.0", "id": 1, "result": {}}`` olur.
Olası hatalar için bölüm 7'ye bakın.

Asistan tarafında ise ilk deneme için şu sorular uygundur:

- "Odoo'da hangi modüller kurulu, satışla ilgili modelleri listele."
- "En son oluşturulmuş 5 müşteriyi adı ve şehriyle göster."
- "Bu ay onaylanmış satış siparişlerinin toplam tutarı ne?"

2.7 Desteklenen MCP sürümleri
-----------------------------

MCP protokolü 2026-07-28 revizyonuyla el sıkışmasız, "her istek kendi
sürümünü taşır" modeline geçti. BigMCP her iki modeli de aynı adreste sunar;
bağlanan istemci hangisini konuşursa onunla anlaşılır:

=======================================  ================================================
İstemci                                  Sonuç
=======================================  ================================================
2026-07-28 ve sonrası (modern)           Çalışır. ``server/discover`` ile sürüm ve
                                         yetenekler alınır, her istek kendi başına
                                         doğrulanır.
2025-11-25, 2025-06-18, 2025-03-26       Çalışır. ``initialize`` el sıkışması yapılır,
(el sıkışmalı)                           istemcinin istediği sürüm geri bildirilir.
Her iki modeli deneyen (çift çağlı)      Çalışır. İstemci önce modern isteği dener ve
                                         başarılı olur; eski yola düşmesi gerekmez.
=======================================  ================================================

Kullanıcı olarak yapmanız gereken bir şey yok; bu ayrım istemciyle sunucu
arasında kendiliğinden çözülür.

----

3. Ayarlar
==========

**Ayarlar > BigMCP** sayfasında üç ayar bulunur (sol menüde modülün ikonuyla
listelenir; yalnızca **MCP Admin** rolündekiler görür):

- **MCP Result Limit (tokens)** — tek bir cevabın en büyük boyutu (3.1–3.4).
- **MCP Cache Duration (minutes)** — istemcinin araç listesini ve genel notları
  yeniden sormadan ne kadar süre kullanabileceği (3.5).
- **MCP Allowed Origins** — tarayıcıdan gelen bağlantılara hangi sitelerin
  izinli olduğu (3.6).

3.1 Sonuç sınırı nedir?
-----------------------

Asistan Odoo'ya her soru sorduğunda (bir arama, bir model açıklaması, bir
metot çağrısı) Odoo'dan bir cevap metni döner. Bu ayar, **tek bir cevabın en
fazla ne kadar büyük olabileceğini** belirler. Birim "token"dır: yapay zekâ
modellerinin metni ölçme birimi; kabaca **1 token ≈ 3 karakter** sayabilirsiniz.
Varsayılan değer **25.000 token**, yani yaklaşık 75.000 karakterlik bir
cevaptır. Bu, birkaç alanlı 80 kayıtlık bir listeyi rahatça sığdırır; ama
"bütün siparişleri bütün alanlarıyla getir" gibi bir istek sığmaz.

3.2 Neden böyle bir sınır var?
------------------------------

Asistanın bir "çalışma belleği" vardır ve Odoo'dan gelen her cevap bu belleğe
yazılır. Sohbet sürdükçe asistan bu belleği her adımda baştan okur. Bu yüzden:

- **Maliyet:** büyük bir cevap, yalnızca geldiği anda değil, sohbetin geri
  kalanındaki her mesajda yeniden ücretlendirilir. Tek bir dikkatsiz sorgu
  sohbetin tamamını pahalılaştırır.
- **Kapasite:** belleğin bir tavanı vardır. Çok büyük bir cevap bu tavanı
  aşarsa asistan hata verir ya da sohbetin başını unutur.
- **Kalite:** asistan on binlerce satırın içinde aradığını bulmakta
  zorlanır; daraltılmış bir sorgu hem daha hızlı hem daha doğru cevap üretir.

Sınır, asistanı küçük ve hedefli sorgular yazmaya yönlendiren bir emniyet
kemeridir.

3.3 Sınır aşılınca ne olur?
---------------------------

1. İşlem Odoo'da **tam olarak çalışır**; kesilen şey yalnızca asistana giden
   cevap metnidir. Bir kayıt oluşturma ya da onaylama çağrısı kesilmişse
   kayıt yine de oluşmuş ya da onaylanmıştır.
2. Asistana cevabın ilk kısmı ve sonunda şu anlamda bir uyarı gönderilir:
   *"Cevap yaklaşık X token, yalnızca ilk 25.000'i gösterildi. Çağrı
   tamamlandı, aynısını tekrarlama; daha az alan ya da daha az kayıt iste."*
3. Asistan bu uyarıyı anlar ve genellikle kendiliğinden daha dar bir sorgu
   kurar: daha az alan ister, sayfa boyutunu düşürür ya da sayım/toplam için
   kayıt listesi yerine gruplama araçlarını kullanır.

Sohbette "sonuç kesildi" ifadesi görürseniz endişelenmeyin; asistan ikinci
denemede genellikle doğru cevaba ulaşır.

3.4 Hangi değeri seçmeli?
-------------------------

Çoğu kurulum için **varsayılan değer uygundur**; ayara dokunmanız gerekmez.
Değiştirmeyi düşünebileceğiniz durumlar:

=========================================  ================================================
Durum                                      Öneri
=========================================  ================================================
Asistan maliyeti yüksek geliyor, çok       Değeri **10.000–15.000**'e düşürün. Asistan
kullanıcı var.                             daha sık daraltma yapar ama her sohbet
                                           daha ucuz olur.
Geniş raporlar (yüzlerce satır, çok        Değeri **40.000–50.000**'e çıkarın. Kullandığınız
sütun) sık sık kesiliyor.                  modelin bellek tavanını aşmamaya dikkat edin.
Belirli bir sorgu kesiliyor, diğerleri     Sınırı değiştirmek yerine asistana isteği
sorunsuz.                                  daraltmasını söyleyin ("sadece ad ve tutarı
                                           getir", "ilk 50 kaydı göster").
=========================================  ================================================

Alanı boş bırakmak ya da ``0`` yazmak ayarı siler; modül yeniden varsayılan
25.000 token değerine döner. Değişiklik kaydedildiği anda geçerlidir; sunucu
yeniden başlatılmaz, asistanın yeniden bağlanması gerekmez.

3.5 Önbellek süresi (MCP Cache Duration)
----------------------------------------

Asistan istemcisi her sohbette, bazen her mesajda "hangi araçlar var, sunucu
talimatları ne?" diye sorar. Bu cevaplar nadiren değişir; o yüzden BigMCP
istemciye "bu cevabı şu kadar dakika sakla, yeniden sorma" der. Varsayılan
**10 dakika**.

Süre yalnızca iki şeyi etkiler: araç listesi (hiç değişmez) ve **genel MCP
notları** (yönetici değiştirdikçe değişir). Yani yeni yazdığınız bir genel
not, asistana en geç bu süre kadar gecikmeyle ulaşır. Model ve metot notları
bundan etkilenmez; onlar her incelemede taze gider.

- Notları sık düzenliyor ve hemen etkisini görmek istiyorsanız süreyi
  kısaltın (ör. 1).
- Not değişikliği nadirse ve istemci trafiğini azaltmak istiyorsanız uzatın
  (ör. 60).
- Boş bırakmak ya da ``0`` yazmak varsayılan 10 dakikaya döndürür; önbelleği
  tamamen kapatmanın yolu yoktur, 1 dakika en kısa pratik değerdir.

Bu süre yalnızca 2026-07-28 ve sonrası istemcilerde kullanılır; eski
istemciler bu bilgiyi almaz ve bugünkü gibi her seferinde sorar.

3.6 İzinli kaynaklar (MCP Allowed Origins)
------------------------------------------

Bir web sayfası, kullanıcının tarayıcısı üzerinden ``/mcp`` adresine istek
gönderebilir; tarayıcı bu isteğe sayfanın adresini (**Origin**) ekler.
MCP güvenlik kuralı, sunucunun bu adresi kontrol edip tanımadığı sitelerden
gelen istekleri reddetmesini (``403``) öngörür; böylece kötü niyetli bir site,
tarayıcınızdaki oturumu kullanarak Odoo'nuza erişemez. BigMCP bu kontrolü
**varsayılan olarak kapalı** tutar ve kararı size bırakır:

- **Yıldız (``*``, varsayılan):** her site kabul edilir; kontrol fiilen
  kapalıdır. Alanı boş bırakmak da bu anlama gelir.
- **Adres listesi:** virgülle ayrılmış siteler, ör.
  ``https://claude.ai, https://app.sirketiniz.com``. Yalnızca listedekiler ve
  Odoo'nun kendi adresi kabul edilir. Tarayıcı erişimini tamamen Odoo'nun
  kendi adresine kısıtlamak için listeye yalnızca o adresi yazın.

Claude Desktop, Claude Code ve sunucudan sunucuya bağlanan bağlayıcılar
Origin başlığı göndermez; onlar bu ayardan hiçbir durumda etkilenmez. Kontrolü
açmak istiyorsanız (adres listesi girerseniz) kullandığınız tarayıcı tabanlı
MCP istemcilerinin adreslerini listeye eklemeyi unutmayın; aksi halde ``403``
alırlar.

----

4. Asistan Odoo'da Ne Yapabilir?
================================

Bağlanan asistan, ilgili kullanıcının yetkileri dahilinde:

- **Okuyabilir:** kayıt arama, listeleme, sayma, gruplama ve toplama
  (ör. müşteri bazında ciro, ürün bazında stok).
- **Yazabilir:** kayıt oluşturma ve güncelleme (yeni müşteri, teklif satırı
  ekleme, not düşme).
- **İş akışı çalıştırabilir:** teklif onaylama, fatura doğrulama, transfer
  tamamlama gibi Odoo'daki düğmelere karşılık gelen metotları çağırma.
- **Silebilir:** kullanıcı Odoo'da silebiliyorsa asistan da silebilir.

Veri değiştiren araç (``call_method``) asistana "tehlikeli olabilir" olarak
işaretlenmiştir; Claude istemcileri bu tür çağrılardan önce genellikle onay
ister. Yine de asıl güvence kullanıcının Odoo yetkileridir (bkz. bölüm 6).

Arşivlenmiş kayıtlar, siz açıkça istemedikçe aramalara dahil edilmez. Resim ve
dosya alanları içerik yerine boyut olarak döner; böylece büyük dosyalar
asistanı yormaz.

----

5. MCP Notları
==============

5.1 Not nedir, neden gerekir?
-----------------------------

Asistan Odoo'nun teknik yapısını kendisi keşfeder, ama **sizin** şirketinizin
kurallarını bilemez: "bayi" dediğinizde hangi müşteri etiketini kastettiğinizi,
siparişlerin neden iptal edilmemesi gerektiğini, hangi alanın aslında ne
anlama geldiğini. **MCP notu**, bu bilgiyi asistana aktarmanın yoludur:
Odoo'ya yazdığınız kısa bir açıklama, asistan ilgili konuya baktığında
otomatik olarak ona gösterilir.

Notlar, yapay zekâ için yazılmış kısa bir "şirket el kitabı" gibi düşünülebilir.
Kod yazmak gerekmez; düz cümleler yeterlidir.

5.2 Üç kapsam
-------------

Bir notun kime, ne zaman gösterileceği **Model** ve **Method** alanlarının
doldurulup doldurulmadığına göre belirlenir:

======================  ==========================================================
Kapsam                  Ne zaman gösterilir?
======================  ==========================================================
**Genel**               Model boş. Asistan bağlanır bağlanmaz, her sohbetin
(model yok)             başında gösterilir. Şirket geneli kurallar ve
                        terimler için.
**Model notu**          Model dolu, metot boş. Asistan o modeli incelediğinde
                        (``describe_model``) gösterilir. Alan anlamları,
                        durum kodları, "şunu yapma" uyarıları için.
**Metot notu**          Model ve metot dolu. Asistan o metodu incelediğinde
                        gösterilir; model notunda da "bu metot için not var"
                        diye işaret edilir. Tek bir işlemin kuralları için.
======================  ==========================================================

5.3 Not yazma
-------------

Notlar **Ayarlar > Teknik > MCP Notes** menüsündedir (Teknik menüsü için
geliştirici modunun açık olması gerekir). Yalnızca **MCP Admin** rolündeki
kullanıcılar yazıp düzenleyebilir.

1. **Yeni**'ye basın.
2. **Başlık**: notun kısa adı. Asistana ``- Başlık: içerik`` biçiminde
   gösterilir; başlık da bilgi taşır, anlamlı seçin.
3. **Model**: ilgili modeli seçin ya da genel not için boş bırakın.
4. **Metot**: Model seçildiyse görünür. Tek bir metodu hedefliyorsanız teknik
   adını yazın (ör. ``action_confirm``, ``unlink``).
5. **Sıra**: Aynı kapsamdaki notların gösterim sırası; küçük sayı önce gelir.
6. **İçerik**: asistanın bilmesi gerekenler.
7. Kaydedin. Not, asistanın bir sonraki bağlantısında ya da model
   incelemesinde devreye girer; sunucuyu yeniden başlatmak gerekmez.

Modül, kurulumla birlikte **ORM vocabulary** adlı bir genel not getirir
(create = ekle, write = güncelle, unlink = sil…). Dokunmanız gerekmez; isterseniz
düzenleyebilirsiniz.

5.4 Örnekler
------------

**Genel not — şirket terimleri**

  :Başlık: Company glossary
  :Model: *(boş)*
  :İçerik: "Bayi" means a partner tagged with the category "Dealer"
           (res.partner.category). "Merkez" is the company
           "Eurotray Merkez" (company id 1). Amounts are in TRY unless the
           record says otherwise; prices exclude VAT.

**Genel not — davranış kuralı**

  :Başlık: Ask before changing data
  :Model: *(boş)*
  :İçerik: Before creating, updating or deleting any record, summarise what
           will change and wait for the user's explicit confirmation. Never
           delete records: archive them instead (write active = false).

**Model notu — satış siparişi**

  :Başlık: Order states
  :Model: Sales Order (``sale.order``)
  :İçerik: state 'draft' and 'sent' are quotations, 'sale' is a confirmed
           order, 'cancel' is cancelled. "Open orders" means state = 'sale'
           with invoice_status != 'invoiced'. The custom field
           x_project_code holds the customer's project reference and is
           mandatory for dealers.

**Model notu — müşteri**

  :Başlık: Customer vs vendor
  :Model: Contact (``res.partner``)
  :İçerik: Customers have customer_rank > 0, vendors have supplier_rank > 0.
           Use company_type = 'company' for companies; individual contacts of
           a company have parent_id set. Phone numbers are stored in 'phone';
           there is no separate mobile field.

**Metot notu — sipariş onaylama**

  :Başlık: Confirmation rule
  :Model: Sales Order (``sale.order``)
  :Metot: ``action_confirm``
  :İçerik: Only confirm an order when the user asks for it explicitly and the
           order has at least one line. Confirmation creates a delivery and
           cannot be undone from the assistant; tell the user this first.

**Metot notu — silme yasağı**

  :Başlık: Do not delete invoices
  :Model: Journal Entry (``account.move``)
  :Metot: ``unlink``
  :İçerik: Posted invoices must never be deleted; legal numbering would break.
           Use button_draft + button_cancel to cancel, or create a credit note
           with action_reverse.

5.5 İyi not yazma ipuçları
--------------------------

- **Kısa ve kesin yazın.** Her notun içeriği asistanın belleğinde yer kaplar;
  gereksiz uzun notlar hem maliyet hem dikkat dağıtır.
- **Asistanın diliyle yazın.** Not hangi dilde yazılırsa asistan o dili
  okur; teknik adları (``sale.order``, ``action_confirm``) olduğu gibi
  bırakın.
- **Doğru kapsamı seçin.** Her sohbette gerekmeyen bir bilgiyi genel not yapmayın;
  ilgili modele ya da metoda bağlayın. Genel notlar her bağlantıda gönderilir.
- **Yasakları açıkça yazın.** "Şunu yapma" cümleleri asistanın en iyi
  uyduğu talimatlardır. Ancak bunlar birer ricadır, gerçek engel değildir;
  kesin yasaklar için Odoo yetkilerini kullanın (bölüm 6).
- **Kullanıcıyı gözlemleyin.** Asistan bir soruyu yanlış anladığında ya da
  yanlış alanı kullandığında, o yanlışı düzelten bir not yazın. Notlar bu
  şekilde zamanla olgunlaşır.

----

6. Güvenlik Notları
===================

- **Her çağrı, anahtarın sahibi kullanıcı olarak çalışır.** Erişim hakları ve
  kayıt kuralları Odoo arayüzündeki gibi uygulanır. Asistana verilen hesap ne
  kadar yetkiliyse asistan o kadar şey yapabilir; en az yetkili uygun hesabı
  tercih edin.
- **MCP User rolü şarttır.** Rolü olmayan kullanıcı, geçerli anahtarla bile
  reddedilir. Bir kullanıcının asistan erişimini kesmek için rolü boşaltmak
  yeterlidir; anahtarını silmeye gerek yoktur.
- **Anahtarlara süre verin.** Süresi dolan anahtar kendiliğinden kapanır.
  Çalışan ayrılınca ya da cihaz kaybolunca anahtarı profil ekranından silin.
- **HTTPS kullanın.** Anahtar her istekte başlık olarak gider.
- **MCP notları bir engel değildir.** Asistan nota uymayabilir; gerçek
  kısıtlamaları Odoo yetkileriyle kurun.
- **Yapılan her araç çağrısı** Odoo sunucu günlüğüne hangi kullanıcının hangi
  aracı hangi parametrelerle çağırdığı bilgisiyle yazılır.

----

7. Sorun Giderme
================

=====================================================  ==============================================
Belirti                                                Çözüm
=====================================================  ==============================================
``401 Invalid apikey``                                 Anahtar yanlış, silinmiş ya da süresi dolmuş.
                                                       Yeni anahtar üretin. Başlığın
                                                       ``Bearer`` + boşluk + anahtar biçiminde
                                                       olduğundan emin olun.
``401 User not authenticated``                         İstek hiç Authorization başlığı taşımıyor.
                                                       İstemci ayarındaki başlığı kontrol edin.
``403 User is not a member of the MCP User group``     Kullanıcıya MCP rolü verilmemiş
                                                       (bölüm 2.3).
``403 Origin not allowed``                             İstek bir tarayıcıdan geliyor ve sitesi
                                                       izinli değil. Adresi **MCP Allowed
                                                       Origins** ayarına ekleyin (bölüm 3.6).
``400 Unsupported protocol version``                   İstemci BigMCP'nin bilmediği bir MCP
                                                       sürümü istiyor. Cevaptaki ``supported``
                                                       listesi desteklenenleri gösterir;
                                                       istemciyi güncelleyin.
``400 Header mismatch``                                İstemci modern sürümün zorunlu
                                                       başlıklarını eksik ya da hatalı
                                                       gönderiyor; istemci tarafı sorunudur.
``404 Method not found``                               Modern istemci, BigMCP'nin sunmadığı bir
                                                       işlev istedi (ör. kaynaklar, abonelik).
                                                       Yalnızca araçlar desteklenir.
Asistan "Truncated… ask for fewer fields" diyor        Sonuç boyut sınırını aştı. Asistanın
                                                       isteği daraltmasını bekleyin ya da
                                                       **MCP Result Limit** ayarını büyütün.
Asistan bir modeli bulamıyor                           Kullanıcının o modele okuma yetkisi yok ya da
                                                       asistan yanlış terimle arıyor. Teknik adı
                                                       söyleyin (ör. faturalar ``account.move``)
                                                       ya da bir genel notla terimi tanımlayın.
Asistan şirket kurallarını bilmiyor                    İlgili bilgiyi MCP notu olarak yazın
                                                       (bölüm 5).
Claude Desktop sunucuyu göstermiyor                    Yapılandırma dosyasının geçerli JSON
                                                       olduğundan, Node.js'in kurulu olduğundan ve
                                                       uygulamanın tamamen kapatılıp açıldığından
                                                       emin olun.
=====================================================  ==============================================
