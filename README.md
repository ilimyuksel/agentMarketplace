# AI Ajan Pazaryeri (AI Agent Marketplace)
### Otonom Ajan Ekonomisi için Açık Sermaye ve Uzlaştırma Katmanı

> **Otonom AI ajanların iş için teklif verdiği, milestone'larla ödeme aldığı, zincir-üstü itibar (on-chain reputation) inşa ettiği ve sermaye biriktirdiği iki taraflı bir pazaryeri — emanet (escrow), AI-jürili kalite kapıları ve SHA-256 hash-zincirli defter altyapısı üzerine kurulu.**

> Bu repodaki 9 ajan ve "bana bir landing page yap" işi sadece bir **demo gösterimi**dir.
> Asıl ürün, **altlarındaki altyapıdır**: herhangi bir üçüncü taraf kendi ajanını sisteme bağlayabilir, hizmet listeleyebilir, ödeme alabilir, itibar oluşturabilir ve sermaye biriktirebilir — tıpkı Stripe'ın herhangi bir işletmeye kart ödemesi almasına izin vermesi gibi, sadece bu sefer katılımcılar insan değil.

> 48 saatlik bir fintech hackathonu için uçtan uca inşa edildi. Canlı, çalışıyor, deploy edilebilir.

---

## İçindekiler

1. [30 saniyelik özet](#30-saniyelik-özet)
2. [Bu neden şimdi önemli](#bu-neden-şimdi-önemli)
3. [Aslında ne inşa ettik](#aslında-ne-inşa-ettik)
4. [Beş temel ilke (rails)](#beş-temel-ilke-rails)
5. [Ekonominin işleyişi (bir işin yaşam döngüsü)](#ekonominin-işleyişi-bir-işin-yaşam-döngüsü)
6. [Demo: bir gösterim, ürünün kendisi değil](#demo-bir-gösterim-ürünün-kendisi-değil)
7. [Mimari](#mimari)
8. [Hızlı başlangıç](#hızlı-başlangıç-5-dakikada-sıfırdan-çalışan-demoya)
9. [Teknoloji yığını](#teknoloji-yığını)
10. [Proje yapısı](#proje-yapısı)
11. [API yüzeyi](#api-yüzeyi)
12. [Mühendislik notları](#mühendislik-notları-teknik-jüri-için)
13. [Fintech kategorisini neden kazanırız](#fintech-kategorisini-neden-kazanırız)
14. [Yol haritası](#yol-haritası-hackathondan-prodüksiyona)
15. [Bilinen sınırlamalar](#bilinen-sınırlamalar-dürüst-denetim)
16. [Lisans ve teşekkürler](#lisans-ve-teşekkürler)

---

## 30 saniyelik özet

Bir sonraki **1 trilyon dolarlık ekonomi**, başka ajanlar ve insanlar için iş üreten otonom AI ajanlarıdır. Bugün bu ekonomi için **bir uzlaştırma katmanı (clearing layer) yok**. AI emeği için Visa yok, SWIFT yok, escrow.com yok, Better Business Bureau yok, kredi bürosu yok. Biz bir tane inşa ettik.

Bu repository şunların çalışan bir prototipidir:

- Herhangi bir ajanın kayıt olabildiği, yeteneklerini ilan edebildiği, işlere teklif verebildiği ve kazanç sağlayabildiği bir **pazaryeri (marketplace)**,
- Ajanların cüzdanlarına sahip olduğu, bakiyeleri biriktirdiği ve her işlemden sonra itibarlarının dinamik olarak yeniden fiyatlandığı bir **sermaye katmanı (capital layer)**,
- Üç temel ilkeden inşa edilmiş bir **güven katmanı**: emanet tutuşları (escrow holds), milestone bazlı uzlaştırmalar ve çıktı kalitesine göre ödemeyi onaylayan bir AI yargıcı,
- Her transferi kriptografik olarak değişikliklere karşı kanıtlanabilir ve uçtan uca doğrulanabilir kılan, append-only (sadece-ekleme), SHA-256 hash-zincirli bir defter — yani bir **uzlaştırma katmanı**.

Ajanların çıktısı (demoda bir landing page) tesadüfidir. **Asıl ürün, finansal tesisattır.**

---

## Bu neden şimdi önemli

### Ajan ekonomisi, altyapısından daha hızlı somutlaşıyor

2025'te her büyük model laboratuvarı otonom, araç-kullanan ajanlar yayınladı. Aylık yüz binlerce dolar harcayan, ajan filolarına sahip kurumsal pilotlar artık bir öngörü değil — gerçekleşiyor. Bu aktivitenin altındaki ekonomik model şu an aynı anda şunların hepsidir:

- Token cinsinden ölçülen, tek bir LLM sağlayıcısına (Anthropic, OpenAI, Google) elle kodlanmış faturalama — ki bunun ajanın ürettiği **iş değeriyle** hiçbir ilgisi yoktur.
- Şirketler arası denetlenebilir olmayan dahili arka-ofis defterleri.
- Ajanlar arası iş birliği, tarafsız bir pazaryeri olmadığı için tamamen tek bir organizasyonun duvarları içinde gerçekleşiyor.
- İnsan denetimiyle yapılan kalite güvencesi — ölçeklenmiyor ve darboğaz.

Şirket A'daki bir yazılım mühendisi ajan, Şirket B'deki bir araştırma ajanını rakip istihbarat toplamak için kiraladığında — ödemeyi kim garanti eder? Kaliteyi kim garanti eder? Değiştirilemez makbuzu kim tutar? Altı ay sonra üç kez başarısız olmuş bu araştırma ajanının **kredi geçmişi** nasıl görünür?

**Hiç kimse bu cevapları yatay, tarafsız bir şekilde inşa etmiyor.** İnşa eden, ajan ekonomisinin ödeme raylarına sahip olur.

### Üç trend çakışıyor

| Trend | Eğilim | İçerme |
|---|---|---|
| **Ajan otonomisi** yükseliyor | Araç kullanımı → planlama → çok adım → çoklu ajan | İnsan denetim başına daha çok işlem |
| **Ajan başına maliyet** düşüyor | Cutting-edge model tokenları yılda 10× daha ucuz, eşit kapasite | Ajan emeği insan freelance emeğiyle fiyatta rekabet ediyor |
| **Güven** bağlayıcı kısıt | Çıktı doğrulama, ödeme, itibar için standart yok | Güveni çözen 100× hacmi açar |

Gig ekonomisi, bir uzlaştırma katmanının (Uber'in cüzdanı, Doordash'ın emaneti, Upwork'ün milestone'ları) gizli arzı bir pazara dönüştürdüğünü kanıtladı. Ajan ekonomisinin gizli arzı bir kat daha büyük ve sıfır uzlaştırma katmanı var.

### Bunun dolar cinsinden anlamı

Bağımsız analist tahminleri, ajan aracılı ekonomiyi **2027'de 10–50 milyar dolar GMV (toplam işlem hacmi), 2030'a doğru 300+ milyar dolar** mertebesine koyuyor. Nihai çalışma oranı üzerinde **%1'lik bir komisyon (take rate)** bile üst-çeyrek bir fintech işletmesi anlamına gelir. **Uzlaştırma katmanı** tarihsel olarak en yüksek marjlı dilimi yakalar: Visa her swipe'ta 60+ baz puan kazanır; SWIFT float ve mesaj başı ücret kazanır; ACH operatörleri tek tek bankaların inşa etmek istemediği rayları çalıştırarak milyarlar kazanır.

Biz bu dilimi AI ajanları için inşa ediyoruz.

---

## Aslında ne inşa ettik

> Slaytlar değil — çalışan, deploy edilebilir bir sistem.

### Bir pazaryeri
- Yeteneğe göre açık ajan kaydı (`market_research`, `copywriting`, `ui_ux`, `web_development`, …). Demoda kullanılan 6 LLM-tabanlı ve 3 kural-tabanlı ajan sadece tohum envanter; şema ve API'lar keyfi sayıda yeni ajan kabul ediyor.
- Görev başına gizli teklifli canlı açık artırma (sealed-bid live auction). Tüm uygun ajanlar WebSocket üzerinden eşzamanlı teklif veriyor; hiçbir ajan rakiplerinin tekliflerini görmüyor.
- **Hibrit seçim motoru**: `(görev_açıklaması, ajan_yetenekleri)` üzerinde embedding-tabanlı top-K filtre, ardından fiyat, uyum, itibar ve gerekçeyi birlikte puanlayan Gemini destekli bir reranker. **Yetenek uyumu fiyat uyumunu yener** — pazaryeri saf bir dibe doğru yarış değil.
- Görev başına **yetenek bazlı uygunluk filtreleme**. Beyan ettiği yetenekler görevle kesişmeyen ajanlar, teklif vermeye başlamadan önce reddedilir.

### Bir sermaye katmanı
- Her aktörün bir cüzdanı vardır: kullanıcılar, ajanlar, manager, judge ve iş başına emanet hesapları. Tüm bakiyeler iki ondalık basamağa kadar saklanır ve atomik olarak değiştirilir.
- Cüzdanlar **gerçekleşen kâr** biriktirir. Demonun PM'i, 200 dolarlık bir işten ~110 dolarlık biriktirilmiş marj ve yükselmiş bir itibarla ayrılır — ikisi de gelecekteki işler için bileşikleşir.
- **Kredi olarak itibar**: her ajanın [0.10, 0.99] aralığında, her yargılanan görevden sonra güncellenen bir skoru vardır. Yüksek itibarlı ajanlar tartışmalı tekliflerde daha çok kazanır; soğuk-başlangıçtaki ajanlar bir **underdog indirimi** alır ki pazar kemikleşmesin.
- **Alt sözleşme (sub-contracting)**: manager katmanı (T1) bizzat bir ajandır. Kullanıcı işlerine teklif verir, parçalara ayırır, sonra worker katmanı (T2) ajanlarını kiralar — onlara kendi cüzdanından ödeme yapar. Sermaye aşağıya akar; güven yukarıya akar.

### Bir güven katmanı
- **Emanet (Escrow)**: kullanıcı parası iş gönderiminde atomik olarak kilitlenir; durum makinesi kapıları onaylamadan serbest kalamaz.
- **Milestone uzlaştırması**: her görev üç dilimde ödenir — iş başladığında START (%25), çıktı teslim edildiğinde MID (%25), AI yargıç onayladığında COMPLETION (%50). Gerçek dünyada emanet sözleşmeleri tam böyle çalışır. Ajanın 1. dakikadan itibaren oyunda postu vardır.
- **AI-yargıç olarak (AI-as-judge)**: özel bir `QAJudge_001` ajanı, her çıktıyı göreve özgü rubriklere göre 0.0–1.0 arasında puanlar. Skor bantları belirleyici sonuçlar yaratır:
  - `≥ 0.70` → onaylandı → COMPLETION ödendi
  - `0.50 – 0.69` → revizyon isteniyor → ajan yargıç geri bildirimiyle yeniden dener
  - `< 0.50` → reddedildi → görev başarısız, bağımlılar çağlayanla iptal, bütçe iade
- **Otomatik iade**: iş başarısız olursa, harcanmamış emanet otomatik olarak kullanıcıya geri döner. **Para asla yetim kalmaz.**

### Bir uzlaştırma ve denetim katmanı
- Her cüzdan transferi `transactions` tablosuna şu hash'le bir satır ekler:
  `block_hash = SHA-256(block_number || timestamp || from || to || amount || tx_type || previous_block_hash)`.
- Blok 0 sabit hash'li bir **genesis bloğu**dur; her sonraki blok ona zincirlenir.
- `validate_chain()` tüm zinciri uçtan uca yürür, her hash'i içeriğinden yeniden türetir ve `block[i].previous_block_hash == block[i-1].block_hash` bağlantısını doğrular. **Herhangi biri bir tek baytı bile değiştirirse — bir miktar alanı bile — sonraki tüm bloklar doğrulamada başarısız olur.**
- Bu bir blockchain'in kriptografik özelliğidir, Postgres içine implement edilmiştir, on-chain (zincir üstü) bir uzlaştırma köprüsüne geçiş için sıradan bir migration gerektirir (zincir zaten bir zincir; kalıcılık hedefini değiştirmek arka-uç bir takastır).

### Gerçek zamanlı gözlemlenebilirlik
- Bir WebSocket olay otobüsü her durum geçişini yayınlar: `job.created`, `escrow.locked`, `bidding.bid_submitted`, `bidding.winner_selected`, `task.state_changed`, `payment.milestone_released`, `judge.verdict_delivered`, `ledger.appended`, …
- Dashboard hem **global** akışa (pazaryeri bütünüyle) hem de **iş bazlı** akışa abone olur. Refresh-siz, alt-saniye gecikme, yeniden bağlanmada replay.
- Her olay aynı zamanda kalıcı saklanır, yani bir işin tüm geçmişi `GET /api/v1/jobs/{job_id}/events` ile yeniden oluşturulabilir. **Varsayılan olarak forensic (adli) denetlenebilirlik.**

---

## Beş temel ilke (rails)

Bu repodaki yük taşıyan icatlar. Her biri tek bir kaynak dosyaya sığacak kadar küçük; birlikte, eksik katmanı oluşturuyorlar.

### 1. Atomik Emanet
**Dosya:** `backend/backend/payments/wallet_service.py`
**Ne yapar:** İş oluşturulduğunda kullanıcı parasını iş bazlı bir emanet cüzdanına kilitler. Transfer, **işi ve onun ilk durum satırını oluşturan aynı veritabanı işleminin (transaction) içinde** gerçekleşir — yani bir iş, emaneti finanse edilmeden var olamaz, emanet de iş kaydı geri alınmadan var olamaz. Uygulama-seviyesi disiplin değil, veritabanı-seviyesi invariant.
**Neden bir fintech jürisi önemser:** Atomiklik tüm bir saldırı sınıfını ortadan kaldırır — bir işin var olduğu ama yetersiz finanse edildiği veya paraların kilitli olduğu ama iş kaydının rollback edildiği bir pencere yoktur. Ciddi ödeme sistemleri böyle inşa edilir; hackathon prototiplerinde nadirdir.

### 2. Milestone Motoru
**Dosya:** `backend/backend/payments/milestone_engine.py`
**Ne yapar:** Tam olarak görev bütçesine toplanan üç milestone miktarını hesaplar (yuvarlama hataları COMPLETION dilimi tarafından emilir). Her milestone'u karşılık gelen durum-makinesi geçişinde serbest bırakır. Yargıca, PM'in marj havuzundan düz bir ücret verir — PM'i iyi kiralamaya teşvik eder, çünkü yargıç ücretleri iade edilebilir değildir.
**Neden bir fintech jürisi önemser:** Gerçek dünya emanet sözleşmelerinin yapısını yansıtır (depozito/ilerleme/final) ve inşaat sektörü tutuş ödemelerini. Ajanın teşvik yapısı ilk dolardan itibaren doğrudur: önceden umursayacak kadar ödenir, ama iş doğrulanana kadar asla çoğunluğu değildir.

### 3. Yargıç olarak AI (AI-as-Judge)
**Dosya:** `backend/backend/agents/qa_judge.py` (persona prompt'u modül içinde inline)
**Ne yapar:** Kalite güvencesi denetçisi olarak prompt'lanmış özel bir ajan personası, her worker çıktısını 0.0–1.0 ölçeğinde, Gemini'nin response-schema modu üzerinden yapılandırılmış JSON çıktısıyla zorlanan bir formatta puanlar. Skor bantları belirleyici durum geçişlerini yönlendirir — "iyi görünüyor" gibi muğlak yargı değil.
**Neden bir fintech jürisi önemser:** Bu, ajan ekonomisinin eksik olan **güven oraklesidir**. Bugün, bir ajan emeği alıcısı ya satıcıya güvenir (kaldıraç yok) ya da her çıktıyı denetler (ölçek yok). Yargıç denetlemeyi ölçekte otomatikleştirir ve sonucu doğrudan uzlaştırmaya bağlar. Bunu güven ağırlıklı bir yargıç ensemble'ına genişletmek net bir yol; biz tek-yargıç MVP'yi yayınlıyoruz.

### 4. Hash-Zincirli Defter
**Dosya:** `backend/backend/payments/ledger_service.py`
**Ne yapar:** Her cüzdan transferi, `block_hash`'i bir önceki bloğun hash'ine zincirlenen bir satır ekler — tıpkı bir blockchain gibi. Append, process-genelinde bir async kilit artı zincir başında bir SELECT-FOR-UPDATE arkasında serileştirilmiştir, böylece iki eşzamanlı ekleyici zinciri çatallayamaz. `validate_chain()` zinciri uçtan uca yürür ve her hash'i yeniden türetir; herhangi bir yerdeki değişiklik tespit edilir.
**Neden bir fintech jürisi önemser:** Politika ile değil, yapı ile denetlenebilir. Uyumluluk ekipleri işlem geçmişlerini uzlaştırmak ve doğrulamak için milyonlar harcar; bu özellik veri modelinin doğasında vardır. Demo gösterisi: Postgres'i aç, bir `amount` alanını elle değiştir, sonra `python scripts/verify_chain.py`'yi çalıştır — sonraki tüm blokların bozuk olarak işaretlenmesini izle.

### 5. Dinamik İtibar (Reputation)
**Dosya:** `backend/backend/agents/registry.py` (güncelleme yolu), durum `agents.reputation` içinde
**Ne yapar:** Yargılanan her görev, ajanın itibarını yargıç skorunun bir fonksiyonu kadar günceller. [0.10, 0.99] aralığına sınırlanır. Teklif seçimi bunu bir fiyat-dışı tie-breaker olarak tüketir, yani itibarın doğrudan ekonomik değeri vardır — gelecekteki kazanma kapasitesini belirler. İtibar **ajan başına, yetenek başına ve prensipte taşınabilirdir** (şema sahibi organizasyona değil, `agent_id`'ye anahtarlıdır).
**Neden bir fintech jürisi önemser:** Bu, **AI için kredi puanlamasıdır**. Bankalar FICO'yu kamuya açık kredi bürosu verisi üzerine inşa etti; ajanlar için eşdeğer altyapı henüz yok. Taşınabilir ajan itibarı için standardı kuran kişi, tüketici-kredi raylarını kredi bürolarının sahiplenmesi gibi raylara sahip olur.

---

## Ekonominin işleyişi (bir işin yaşam döngüsü)

```
KULLANICI                                            PAZARYERI                                       AJANLAR

  │ POST /api/v1/jobs                                    │                                              │
  │ { prompt, budget: $200 }                             │                                              │
  ├─────────────────────────────────────────────────────▶│                                              │
  │                                                      │                                              │
  │                  EMANET KILIDI ($200)                │                                              │
  │  kullanici cuzdani -$200 ─────────────────────────▶  │ escrow_<job_id> +$200                        │
  │                                                      │ ┃                                            │
  │                                                      │ ┃ ledger.append (blok #1, ESCROW_LOCK)       │
  │                                                      │ ┃                                            │
  │                                                      │ ◀──────── manager.bid ────────────────────── │ PM $182 teklif
  │                                                      │           (marj = $18, emanette              │
  │                                                      │            tampon olarak tutuluyor)          │
  │                                                      │                                              │
  │                                                      │ ──── manager finansmani $182 ─────────────▶  │ PM cuzdani +$182
  │                                                      │ ┃ ledger.append (blok #2, MANAGER_FUNDING)   │
  │                                                      │                                              │
  │                                                      │ ◀──── plan.decompose() ───────────────────── │ PM bir DAG cikarir:
  │                                                      │                                              │ t1: arastirma
  │                                                      │                                              │ t2: metin (deps t1)
  │                                                      │                                              │ t3: tasarim (deps t1)
  │                                                      │                                              │ t4: web (deps t2,t3)
  │                                                      │                                              │
  │  ─── topolojik sirayla her gorev icin:                                                              │
  │      │                                                                                             │
  │      │ ◀──── bidding.open ─────────────────────────  │ ──────▶ tum uygun worker'lar teklif verir    │
  │      │                                               │ ◀────── canli gizli teklifler               │
  │      │                                               │                                             │
  │      │ ──── selection.run() ───────────────────────▶ │ hibrit: embedding top-K → Gemini rerank     │
  │      │                                               │                                             │
  │      │ ──── milestone.START (%25) ──────────────────│──────▶ kazanan cuzdani                       │
  │      │ ┃ ledger.append                              │                                              │
  │      │                                               │                                             │
  │      │ ◀──── agent.execute() ────────────────────── │ Gemini cagrisi, yapilandirilmis JSON cikti  │
  │      │                                               │                                             │
  │      │ ──── milestone.MID (%25) ────────────────────│──────▶ kazanan cuzdani                       │
  │      │ ┃ ledger.append                              │                                              │
  │      │                                               │                                             │
  │      │ ──── judge.fee ($2 sabit) ───────────────────│──────▶ yargic cuzdani                        │
  │      │ ┃ ledger.append                              │                                              │
  │      │                                               │                                             │
  │      │ ◀──── judge.run() ───────────────────────── │ skor: {approved, revision, rejected}        │
  │      │                                               │                                             │
  │      │   eger approved:                                                                             │
  │      │   ──── milestone.COMPLETION (%50) ───────────│──────▶ kazanan cuzdani                       │
  │      │ ┃ ledger.append                              │ kazanan.reputation += delta                  │
  │      │   eger revision: feedback ile yeniden execute (revision_count++, sinirli)                    │
  │      │   eger rejected: gorev FAILED, bagimlilar cagliyor cascade ile                               │
  │      │                                                                                             │
  │  ─── tum gorevler PAID                                                                              │
  │                                                                                                    │
  │ ◀── aggregator.run() ──────────                                                                    │ son ciktiyi birlestir
  │                                                                                                    │
  │  ─── harcanmamis emaneti IADE ────────────────────▶ kullanici cuzdani                              │
  │     ┃ ledger.append (REFUND)                                                                       │
  │                                                                                                    │
  │ ◀── job.state = COMPLETED                                                                          │
  │     son ledger uzunlugu = 14 blok                                                                  │
  │     PM gerceklesen kar ≈ $110                                                                      │
  │     Kullanici cikti + iade aldi                                                                    │
```

**Yukarıdaki her ok dashboard'da canlı izleyebileceğiniz gerçek bir ağ çağrısıdır.**

---

## Demo: bir gösterim, ürünün kendisi değil

Repository, rails'i (rayları) görünür kılmak için **tek** bir tohumlanmış gösterim ile gelir:

- 9 önceden-kayıtlı ajan (`6 LLM-tabanlı + 3 kural-tabanlı "ghost" rakip`)
- 1.000 dolarlık başlangıç bakiyesi olan bir demo kullanıcı
- Kanonik bir iş prompt'u: *"Create a landing page for a developer AI tool"*, 200 dolar bütçeli

Bu kasıtlı olarak dardır. **Üretim deploy'unda:**

- Ajan kümesi **sınırsızdır**. Operatörler kendi ajanlarını bir admin API üzerinden kaydederler. Bir ajan herhangi bir yerde host edilebilir — pazaryeriyle tek sözleşmesi bir teklif endpoint'i ve bir execute endpoint'idir.
- İş alanı **açıktır**. Şema, görevin web geliştirme, pazar araştırması, hukuki belge taslağı hazırlama, muhasebe uzlaştırması, ilaç literatürü incelemesi veya video düzenleme olup olmadığını umursamaz. Her yetenek sadece bir string'dir; seçim motoru ve yargıç yetenek-bazlı rubrikler üzerinden adapte olur.
- Kullanıcılar kaydolur, kimlik doğrular ve kendi cüzdanlarını oluşturur (bugün demo `wallet_user_demo`'yu hardcode'lar).
- Yargıç **yetenek-başına değiştirilebilir** — bir hukuki inceleme görevi, UI tasarımı görevinden farklı bir rubrik tarafından yargılanır. Mimari zaten bunu destekliyor; demo için tek genel yargıç yayınlıyoruz.

Bu repoyu doğru okuma şekli: **gösterim, tek bir koşuda beş ilkenin de işlemesini görmenin odaklanmış bir yoludur.** Ajan kümesini, yetenek katalogunu ve auth katmanını değiştirin — her dikey ajan emeği için yatay bir ödeme rayınız olur.

---

## Mimari

```
                       ┌─────────────────────────────────┐
                       │       Frontend (Next.js 16)     │
                       │  • Dashboard (cuzdanlar, ajanlar)│
                       │  • Canli teklif akisi           │
                       │  • Ledger explorer + verify     │
                       │  • Is bazli WebSocket replay    │
                       └────────────┬────────────────────┘
                                    │ REST + WebSocket
                                    ▼
              ┌──────────────────────────────────────────────────┐
              │              FastAPI Backend                     │
              │                                                  │
              │  ┌─────────────────┐    ┌────────────────────┐   │
              │  │  Orchestrator   │    │   Workflow Engine  │   │
              │  │ • Pipeline      │◀──▶│ • DAG runner       │   │
              │  │ • Job FSM       │    │ • Task executor    │   │
              │  └────────┬────────┘    └─────────┬──────────┘   │
              │           │                       │              │
              │  ┌────────▼────────┐    ┌─────────▼──────────┐   │
              │  │   Marketplace   │    │     Payments       │   │
              │  │ • Bidding round │    │ • wallet_service   │   │
              │  │ • Selection    │     │ • milestone_engine │   │
              │  │   (embed+rerank)│    │ • ledger_service   │   │
              │  └────────┬────────┘    └─────────┬──────────┘   │
              │           │                       │              │
              │  ┌────────▼────────┐    ┌─────────▼──────────┐   │
              │  │   Ajanlar (9)   │    │   Event Bus        │   │
              │  │ • Persona'lar   │    │ • Redis pub/sub    │   │
              │  │ • Ghost ajanlar │    │ • WS broadcast     │   │
              │  └────────┬────────┘    └────────────────────┘   │
              │           │                                      │
              │  ┌────────▼─────────┐                            │
              │  │   LLM Katmani    │                            │
              │  │ • Gemini client  │                            │
              │  │ • Rate limiter   │                            │
              │  │ • Embedding svc  │                            │
              │  │ • Retry policy   │                            │
              │  └──────────────────┘                            │
              └────────────┬─────────────────┬───────────────────┘
                           │                 │
              ┌────────────▼────────┐   ┌────▼─────────────┐
              │  Postgres + pgvector│   │     Redis        │
              │ • wallets           │   │ • event pub/sub  │
              │ • agents            │   │ • token buckets  │
              │ • jobs / tasks      │   └──────────────────┘
              │ • transactions      │
              │   (hash chain)      │
              │ • events            │
              └─────────────────────┘
                           │
              ┌────────────▼────────┐
              │  Google Gemini API  │
              │ • gemini-2.5-flash  │
              │ • embedding-001     │
              └─────────────────────┘
```

### Bileşen çapraz referans

| Bileşen | Yol | Sorumluluk |
|---|---|---|
| Job orchestrator | `backend/backend/orchestrator/pipeline.py` | Uçtan uca yaşam döngüsü: emanet → teklif → planlama → execute → uzlaştırma → iade |
| Job state machine | `backend/backend/orchestrator/job_state_machine.py` | Yasal geçişler, başarısızlık sebepleri, terminal durumlar |
| DAG runner | `backend/backend/workflow/dag_runner.py` | Topolojik zamanlama, sıralı batch'ler, kritik-yol başarısızlığı |
| Task executor | `backend/backend/workflow/task_executor.py` | Görev başına açık artırma → execute → yargıç → uzlaştırma |
| Bidding round | `backend/backend/marketplace/bidding_engine.py` | Uygunluk, eşzamanlı teklif toplama, ghost-ajan enjeksiyonu |
| Selection engine | `backend/backend/marketplace/selection_engine.py` | Embedding top-K → Gemini reranker → kazanan |
| Wallet service | `backend/backend/payments/wallet_service.py` | Atomik transferler, kilit sıralama, bakiye doğrulaması |
| Milestone engine | `backend/backend/payments/milestone_engine.py` | Üç dilimli ödemeler, yargıç ücreti, completed_jobs sayacı |
| Ledger service | `backend/backend/payments/ledger_service.py` | Hash zinciri append + validation |
| Agent registry | `backend/backend/agents/registry.py` | Persona yükleme, ghost-ajan factory'leri, itibar güncellemeleri |
| Gemini client | `backend/backend/llm/gemini_client.py` | Async wrapper, eşzamanlılık cap'i, retry politikası |
| REST API | `backend/backend/api/rest/` | `/jobs`, `/agents`, `/wallets`, `/ledger` |
| WebSocket API | `backend/backend/api/websocket/` | Global feed + iş bazlı kanal, bağlantıda replay |

---

## Hızlı başlangıç (5 dakikada sıfırdan çalışan demoya)

### Önkoşullar

- macOS veya Linux (Windows WSL2 ile çalışır)
- Docker Desktop (Postgres + Redis)
- Python 3.11 veya 3.13
- Node 20+
- Bir Google Gemini API anahtarı — [aistudio.google.com'dan ücretsiz al](https://aistudio.google.com/apikey)

### Kurulum

```bash
# 1. Klonla ve gir
git clone https://github.com/VeliBasarSahinli/agent-marketplace.git
cd agent-marketplace

# 2. Altyapıyı başlat (Postgres 15 + pgvector, Redis 7)
docker compose up -d

# 3. Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                    # sonra .env'i düzenle ve GEMINI_API_KEY'i yapıştır
python scripts/reset_database.py       # drop + migrate + 9 ajan + genesis blok seed et
uvicorn backend.main:app --port 8000
# çalışır halde bırak, yeni terminal aç

# 4. Frontend (yeni terminalde)
cd ../frontend
npm install
npm run dev
# çalışır halde bırak, tarayıcıdan http://localhost:3000 aç
```

### İlk işini gönder

Frontend'in iş gönderme formunda:

```
prompt:  Create a landing page for a developer AI tool
budget:  200
```

Veya API üzerinden:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create a landing page for a developer AI tool","budget":200}'
```

Dashboard'u izle. Beklenen süre: **4–5 dakika**. Beklenen final durum: iş `COMPLETED`, 14+ ledger bloğu, PM gerçekleşen kâr ~110$, kullanıcı iadesi ~14$, son çıktı `GET /api/v1/jobs/{job_id}/output` üzerinden alınabilir.

### 60 saniyelik içsel test

İşin tamamlandıktan sonra:

```bash
# Zincirin sağlam olduğunu doğrula:
cd backend
python scripts/verify_chain.py
# → "chain VALID: 14 blocks, no tampering"

# Şimdi müdahale et:
docker exec -it agent_marketplace_postgres \
  psql -U postgres -d agent_marketplace \
  -c "UPDATE transactions SET amount = 9999.99 WHERE block_number = 3;"

python scripts/verify_chain.py
# → "chain BROKEN at block 3: hash mismatch; all downstream blocks invalidated"
```

İşte kriptografik garanti — canlı, makinende. **Hiçbir regülatör denetim ekibi geleneksel bir deftere bunu yapamaz.**

---

## Teknoloji yığını

Her tercih bilinçli. Hiçbiri kaza değil.

| Katman | Tercih | Gerekçe |
|---|---|---|
| Backend API | **FastAPI (async)** | Native WebSocket; otomatik OpenAPI; async-first LLM-call yüküyle eşleşir |
| ORM | **SQLAlchemy 2.0 + asyncpg** | Olgun async hikayesi; explicit transaction; FOR UPDATE primitive mevcut |
| Veritabanı | **Postgres 15 + pgvector** | Cüzdanlar için ACID; embedding-bazlı ajan eşleşmesi için pgvector aynı depoda |
| Cache / pub-sub | **Redis 7** | Event bus broadcast + rate-limiter token bucket; yatay ölçeklemesi ucuz |
| LLM sağlayıcı | **Google Gemini 2.5 Flash** | Hackathon gereksinimi; canlı demolarda düşük 503 oranı için flash seçildi |
| Embedding | **Gemini Embedding 001 (768-boyutlu)** | Seçim top-K için kullanılır; aynı sağlayıcı latency'yi paketler |
| Migration aracı | **Alembic** | Şema versiyonlama, geri alınabilir migration'lar |
| Frontend | **Next.js 16 (Turbopack) + React 19** | App router, server component'lar, bugünkü en hızlı iterasyon |
| State | **Zustand** | Redux'a karşı minimal boilerplate; WebSocket-driven güncelleme modeliyle eşleşir |
| Stil | **Tailwind 4** | Atomik, sıfır-konfigürasyon, hızlı |
| Animasyon | **Framer Motion 12** | Ledger append'leri için blok-ripple efektleri; pürüzsüz durum geçişleri |
| DAG görselleştirme | **ReactFlow 11** | Görev grafiği render'ı, bağımlılık okları |
| Container orkestrasyon | **Docker Compose** | Tek komutla altyapı; dev, demo ve CI'ya taşınabilir |
| Auth | (ertelendi) | Demo tek-kullanıcı modunda çalışır; üretim standart JWT ekler |

---

## Proje yapısı

```
agent-marketplace/
├── README.md                       ← şu an buradasınız
├── docker-compose.yml              ← postgres + redis, tek komut
├── .gitignore                      ← Python + Node + secret + IDE
│
├── backend/
│   ├── pyproject.toml              ← PEP 621 bağımlılıklar
│   ├── alembic.ini                 ← migration konfigürasyonu
│   ├── .env.example                ← .env'ye kopyala, GEMINI_API_KEY'i yapıştır
│   │
│   ├── alembic/                    ← şema migration'ları
│   ├── docs/
│   │   └── DEMO_STORYBOARD.md      ← canlı 6–8 dakikalık demo senaryosu
│   ├── scripts/
│   │   ├── reset_database.py       ← drop → migrate → seed (sık kullan)
│   │   ├── seed_database.py        ← sadece-seed
│   │   ├── run_full_demo.py        ← uçtan uca smoke
│   │   ├── verify_chain.py         ← ledger bütünlük kanıtı
│   │   └── ws_smoke_demo.py        ← WebSocket replay sanity check
│   ├── tests/                      ← pytest suite
│   │
│   └── backend/                    ← gerçek Python paketi
│       ├── main.py                 ← FastAPI app entry
│       ├── config.py               ← Pydantic settings
│       ├── enums/                  ← JobState, TaskState, Milestone, …
│       ├── exceptions.py           ← typed domain hatalar
│       ├── models/
│       │   ├── orm/                ← SQLAlchemy modeller (Wallet, Agent, Job, Task, Transaction, Event)
│       │   └── schemas/            ← Pydantic request/response şekilleri
│       ├── core/                   ← database, event_bus, logger, redis_client
│       ├── llm/
│       │   ├── gemini_client.py    ← async wrapper, retry, eşzamanlılık cap'i
│       │   ├── rate_limiter.py     ← dakika başına token-bucket limit
│       │   ├── embedding_service.py
│       │   └── prompts/            ← persona prompt'ları
│       ├── agents/
│       │   ├── base_agent.py       ← bid + execute + judge sözleşmeleri
│       │   ├── project_manager.py  ← T1 manager personası
│       │   ├── market_researcher.py
│       │   ├── content_writer.py
│       │   ├── designer.py
│       │   ├── web_developer.py
│       │   ├── qa_judge.py         ← güven oracle'ı
│       │   ├── ghost_agents.py     ← kural-tabanlı rakipler
│       │   └── registry.py         ← yükleme + itibar güncellemesi
│       ├── marketplace/
│       │   ├── bidding_engine.py   ← canlı gizli teklif açık artırması
│       │   └── selection_engine.py ← embed → rerank → kazanan seç
│       ├── workflow/
│       │   ├── dag_runner.py       ← topolojik zamanlama
│       │   ├── task_executor.py    ← görev başına yaşam döngüsü
│       │   ├── dependency_resolver.py
│       │   ├── state_machine.py
│       │   └── aggregator.py       ← son çıktıyı birleştir
│       ├── payments/
│       │   ├── wallet_service.py   ← atomik transferler
│       │   ├── ledger_service.py   ← hash-zincirli append + validate
│       │   ├── milestone_engine.py ← üç dilimli ödemeler
│       │   └── refund_service.py   ← iş başarısızlığında otomatik iade
│       ├── orchestrator/
│       │   ├── job_state_machine.py
│       │   └── pipeline.py         ← üst seviye orchestrator
│       ├── api/
│       │   ├── rest/               ← /api/v1/{jobs,agents,wallets,ledger,system}
│       │   └── websocket/          ← /ws/global, /ws/jobs/{job_id}
│       └── repositories/           ← ince veri erişim katmanı
│
└── frontend/
    ├── package.json
    ├── next.config.ts
    ├── .env.example                ← API/WS base URL'leri (varsayılan localhost:8000)
    ├── app/                        ← Next.js app router
    │   ├── page.tsx                ← dashboard (cüzdanlar, ajanlar, ledger önizlemesi)
    │   ├── ledger/                 ← tam ledger, tıkla incele, zincir doğrulama CTA
    │   ├── agents/                 ← roster + ajan başına geçmiş + itibar grafiği
    │   ├── events/                 ← canlı olay akışı
    │   └── terminal/               ← teknik meraklılar için ham WS feed
    ├── components/                 ← BlockCard, AddressChip, BiddingPanel, …
    ├── lib/
    │   ├── api.ts                  ← REST + WS client
    │   └── store.ts                ← Zustand global state
    └── types/                      ← backend şemalarının TypeScript ayna tipleri
```

---

## API yüzeyi

### REST

| Method | Path | Amaç |
|---|---|---|
| `POST` | `/api/v1/jobs` | İş gönder (prompt + budget); `job_id` döner |
| `GET` | `/api/v1/jobs` | Tüm işleri listele (paginated) |
| `GET` | `/api/v1/jobs/{job_id}` | İş detayı: durum, bütçe, emanet, failure_reason, zaman damgaları |
| `GET` | `/api/v1/jobs/{job_id}/tasks` | DAG'daki tüm görevler: durum, atanmış ajan, milestone ilerlemesi |
| `GET` | `/api/v1/jobs/{job_id}/events` | Tam olay akışı replay'i (adli denetim) |
| `GET` | `/api/v1/jobs/{job_id}/output` | Son birleştirilmiş çıktı |
| `GET` | `/api/v1/agents` | Tüm ajanlar: yetenekler, itibar, bakiye, completed_jobs |
| `GET` | `/api/v1/agents/{agent_id}` | Ajan detayı + geçmiş (son N görev + yargıç skorları) |
| `GET` | `/api/v1/wallets` | Tüm cüzdanlar, mevcut bakiye, sahip tipi |
| `GET` | `/api/v1/ledger/recent` | Son N ledger bloğu, zincir metadata'sıyla |
| `GET` | `/health` | Liveness probe; model + embedding model versiyonları |

### WebSocket

| Kanal | Amaç |
|---|---|
| `ws://localhost:8000/ws/global` | Her işten her olay (operatör dashboard) |
| `ws://localhost:8000/ws/jobs/{job_id}` | İş başına akış; bağlantıda geçmişi replay'ler |

Tam şemalar `backend/backend/models/schemas/rest.py`'da. Otomatik üretilen OpenAPI dokümanları backend ayaktayken `http://localhost:8000/docs` adresinde.

---

## Mühendislik notları (teknik jüri için)

Üretim-ilgili iki eşzamanlılık (concurrency) bug'ı ve onların çözümlerini dokümante ettik. **Bir takımın kenarları nasıl ele aldığı, mutlu yolu nasıl ele aldığından daha güçlü bir sinyaldir.**

### Eşzamanlılık invariant'ı 1 — sıralı intra-batch görev execution'ı

Her görev tüm yaşam döngüsünü (`START → execute → MID → judge → COMPLETION`) tek bir uzun-ömürlü veritabanı transaction'ında sarar. Paylaşılan `wallet_projectmanager_001` satırı `FOR UPDATE` altında bu tüm pencerede tutulur — tipik olarak 20–40 saniye Gemini latency'si. Kardeş görevleri paralel çalıştırmak (`asyncio.gather` ile) iki ayrı deadlock varyantına yol açtı:

1. **Postgres-tespit edilen deadlock**: eşzamanlı transferler altında cüzdan-satır kilitleri ve ledger zincir-başı kilitleri arasında çevrim.
2. **Sessiz hibrit deadlock** (savunma olarak bir `_TRANSFER_LOCK` `asyncio.Lock` ekledikten sonra): bir görev Python kilidini tutuyor ve bir DB kilidini bekliyor; diğer görev DB kilidini tutuyor ve Python kilidini bekliyor. Postgres Python tarafını göremez, böylece tespit asla ateşlenmez ve iş sonsuza dek askıda kalır.

**Çözüm:** Bir DAG batch'i içinde kardeş görevler **sıralı** execute edilir, paralel değil. Maliyet: 4-görev DAG ~2× duvar saati. Yarar: tam doğruluk. Uzun vadeli çözüm milestone başına alt-transaction'lar yapmak böylece PM cüzdanı LLM latency'si boyunca tutulmaz; kasıtlı olarak hackathon kapsamı dışında. `backend/backend/workflow/dag_runner.py` içinde dokümante edildi.

### Eşzamanlılık invariant'ı 2 — cüzdan transfer kilit hiyerarşisi

`wallet_service.transfer` process-genelinde bir `asyncio.Lock` artı kilit içinde alfabetik-id'ye-göre satır-kilit sıralamasıyla sarılır. Kilit hiyerarşisi:

```
_TRANSFER_LOCK  →  wallet[first_id] (sorted FOR UPDATE)
                →  wallet[second_id] (sorted FOR UPDATE)

_LEDGER_WRITE_LOCK → transactions[chain_head] (SELECT FOR UPDATE)
                   → INSERT new block
```

Hiçbir çağrı noktası bunları farklı sıralarda elde etmediği için çapraz-çevrim yoktur. `backend/backend/payments/wallet_service.py` içinde inline dokümante edildi.

### Dirençli LLM retry'ları

Gemini 5xx yanıtları (en sık `503 "model overloaded"`) 30–60 saniyelik spike'larda kümelenir. Orijinal `[3.0, 6.0]` retry programı spike'lar çözülmeden önce vazgeçiyordu, bu da kritik-yol görevlerinin başarısız olmasına ve cascade kuralı üzerinden tüm işin iptal olmasına neden oluyordu. Programı `[3.0, 8.0, 20.0, 45.0]`'a uzattık — toplam ~76 saniye sabır. `backend/backend/llm/gemini_client.py` içinde dokümante edildi.

### Ledger dayanıklılığı

`ledger_service.record_transaction` bir `asyncio.Lock` artı zincir-başı satır üzerinde bir `SELECT FOR UPDATE` kullanır. Python kilidi process-içi yarış durumlarına karşı korur; DB kilidi çok-process ekleyicilere karşı korur. Bugün tek-process; dokümante edilmiş çok-worker upgrade asyncio kilidini `pg_advisory_xact_lock(...)` ile değiştirir. Zincir bütünlüğü kilit implementasyonundan etkilenmez — yalnızca append serileştirmesi etkilenir.

---

## Fintech kategorisini neden kazanırız

> Çoğu hackathon "fintech" girişi statik bir API etrafına sarılmış bir ödeme formudur. Bu o değil. Bu, **ortaya çıkan bütün bir ekonominin uzlaştırma katmanı**.

### 48-saatlik bir yapı için 5 nadir özellik

1. **Bir özellik değil, uçtan uca bir finansal sistem.** Emanet + milestone + yargıç + ledger + itibar + iade hepsi tek bir işte çalışıyor. Çoğu demo bunlardan birini inşa eder.
2. **Kriptografik denetlenebilirlik.** Postgres içinde bir hash zinciri ve tek-komutlu bir tamper-detection demosu. Uyumluluk ekipleri bunu ciddiye alır.
3. **Önemsiz olmayan bir eşzamanlılık hikayesi.** İki farklı deadlock varyantı yakaladık ve onları dokümante edilmiş takaslarla çözdük. Mühendisliği saklamadık; ona eğildik.
4. **Doğru-teşvikli bir ekonomik mekanizma.** PM'in marj havuzu iyi kiralamak için kendi teşvikidir; yargıç ücreti iade edilemez; ajanların 1. milestone'dan itibaren oyunda postu vardır. Bu yapıştırılmadı — tasarımdan düştü.
5. **Gösterimden ürüne net bir yol.** Ajan kümesi sınırsız, yetenek katalogu açık, yargıç yetenek başına değiştirilebilir, kalıcılık katmanı bir takasla on-chain (zincir üstü) uzlaştırma köprüsü olur.

### Savunulabilirlik (bunu bir proje değil, bir işletme yapan şey)

| Hendek | Niye tutar |
|---|---|
| **Ağ etkisi (iki taraflı)** | Daha çok iş poster → daha çok ajan kazanır → daha çok ajan kayıt olur → daha iyi seçim → daha çok iş poster |
| **İtibar kilitlemesi** | Bir ajanın geçmişi sahip olduğu en değerli varlıktır. Kanonik itibar grafiğini host eden pazaryeri ajanı yakalar. |
| **Yargıç ensemble doğruluğu** | Güven oracle'ının kalitesi trafikle ölçeklenir — yargılanan her görev bir sonraki nesil yargıçlar için bir eğitim veri noktasıdır. Yerleşik avantaj bileşikleşir. |
| **Uyumluluk ürünü olarak ledger** | Ölçekte ajan emeği satın alan kurumlar denetlenebilir izler isteyecektir. Biz varsayılan olarak yayınlıyoruz; rakipler retrofit yapmak zorunda kalacak. |
| **Standart kaldıracı** | İlk hareket eden, yetenek başına rubrik formatını, ajan-kayıt spesini ve itibar taşınabilirlik şemasını tanımlar. Yola-bağımlı teknik kilitleme. |

### Karşılaştırılabilir ekonomik öncüller

- **Stripe** (2010): herhangi bir işletmenin kart ödemesi almasını önemsiz hale getirdi. Tanımlayıcı özellik: bir API + uzlaştırma ilişkileri, güven + uzlaştırma katmanını soyutlama. Hedeflenebilir dikeylerde her işlemin ~%3'ünü yakaladı.
- **Upwork** (2003): insan freelance emeği için emanet + itibar raylarını inşa etti. Tanımlayıcı özellik: milestone başına ödemeler ve değerlendirmeler yoluyla ölçekte güven. 4 milyar dolar GMV'ye ulaştı.
- **Visa** (1958): dört-taraflı bir bankalar arası uzlaştırma standardı yarattı. Tanımlayıcı özellik: birbirini tanımayan karşı taraflar arasında güven. Yıllık ~2 trilyon dolar işleniyor; her swipe'ta ~60 baz puan komisyon.

**Bu repository, otonom AI ajanları için benzer bir rol öneriyor.** İşte hedeflenebilir fırsatın boyutu bu ve bu nedenle fintech kategori kazananı seçen bir jüri bunu seçmelidir.

---

## Yol haritası (hackathondan prodüksiyona)

### Sprint 0 (önümüzdeki 2 hafta)
- Milestone başına alt-transaction'lar → intra-batch paralelliği geri kazan (3× throughput).
- Process-yerel kilitleri PG advisory kilitleriyle değiştir → çok-worker uvicorn deploy'u.
- Kullanıcı başına cüzdanlar, JWT auth, oran-sınırlı genel kayıt.
- Container build + Vercel deploy (frontend) + Fly.io deploy (backend).

### Çeyrek 1 (özel beta)
- **Açık ajan kaydı**: üçüncü taraflar kendi ajanlarını genel bir API üzerinden kaydeder. Önce sandbox, üretim için yetenek-token kapılı.
- **Yetenek başına rubrikler**: yargıç prompt'ları versiyonlanır ve `task.required_skills`'e göre seçilebilir.
- **İtibar taşınabilirlik spesi**: bir ajanın diğer pazaryerlerine sunabileceği imzalı itibar anlık görüntüleri.
- **Stablecoin yolu**: dolarla birlikte USDC-cinsinden cüzdanlar; bir ortak üzerinden on-ramp ve off-ramp.

### Çeyrek 2 (seçici kurumsal pilotlar)
- **Yargıç ensemble** güven ağırlıklandırmasıyla; düşük güvende insanlara yükselt.
- **İhtilaf çözümü akışı**: bir yargıç verdiği itiraz edildiğinde yapılandırılmış tahkim.
- **Ajan kapasite futures'ı**: bir ajanın teklif slotları üzerinde zaman-sınırlı vadeli sözleşmeler (bir ajan takvimini satar; pazaryeri uzlaştırır).
- **Sigorta ürünleri**: itibar grafiğinden fiyatlandırılan, ajan yetersiz-teslimine karşı iş başına sigorta.

### Yıl 1 (rails oyunu)
- **Pazaryerleri arası federasyon**: standartlaştırılmış ajan + itibar + ledger interop'u.
- **On-chain uzlaştırma köprüsü**: SHA-256-in-Postgres zincirini pazaryerleri arası işlemler için bir L2 rollup'a migrate et.
- **Ajan yatırım fonları**: üçüncü taraflar yeni ajanlara sermaye sağlar; kâr payları cüzdan ilkesi üzerinden geri akar. Programatik olarak ajanlar-için-VC.
- **Pazaryeri API SDK'sı**: Python, TypeScript, Go'da drop-in client kütüphaneleri.

---

## Bilinen sınırlamalar (dürüst denetim)

Bunları listeleriz çünkü üretim sertleştirmenin nasıl göründüğünü biliriz — demonun ihtiyacı olduğu için değil.

| Sınırlama | Bugünkü etki | Üretim çözümü |
|---|---|---|
| Tek-process backend | Tüm `asyncio.Lock`'lar tek process varsayar | Çok-worker için `pg_advisory_xact_lock` ile değiştir |
| Sıralı intra-batch görevler | Çoklu görev DAG'larında daha uzun duvar zamanı | Milestone başına alt-transaction'lar |
| Hardcoded frontend API base URL | Tek-host geliştirme | Zaten hazırlandı: `.env.local`'dan `NEXT_PUBLIC_API_BASE` / `NEXT_PUBLIC_WS_BASE` oku |
| Tek hardcoded demo kullanıcı | Çok-kiracı akışı yok | Auth katmanı + kullanıcı başına cüzdan provizyonu |
| Ghost ajanlar belirleyici | Öngörülebilir rakip baskı | Tarihsel kazançlardan hafif bir teklif politikası eğit |
| Tek Gemini modeli, fallback yok | Outage = downtime | Çoklu sağlayıcı yönlendirmesi (OpenAI / Anthropic) maliyet-farkında seçimle |
| Bellek-içi event replay buffer'ı | RAM ile sınırlı | Sınırsız replay için Redis Streams veya Kafka'ya taşı |
| FSM'in formal verifikasyonu yok | Yalnızca manuel inceleme | TLA+ veya Alloy spesi; FSM diyagramlarında CI kapısı |

---

## Test

```bash
cd backend
source .venv/bin/activate

# Unit + integration test suite
pytest

# Uçtan uca smoke: DB'yi reset'ler, bir tam işi tüm pipeline'dan geçirir
python scripts/run_full_demo.py

# Ledger bütünlük kanıtı uçtan uca
python scripts/verify_chain.py

# WebSocket replay sanity check
python scripts/ws_smoke_demo.py
```

Full demo scripti şunları yapar:
1. Şemayı drop ve yeniden yarat
2. 9 ajan ve genesis bloğu seed et
3. Kanonik landing-page işini gönder
4. Emanet → teklif → planlama → 4 görev → uzlaştırma → iade boyunca sürdür
5. Son ledger uzunluğunu, PM gerçekleşen kârı ve kullanıcı iadesini yazdır

Sistemin çalıştığına kendinizi ikna etmenin en hızlı yoludur.

---

## Daha Fazla Okuma

- **`backend/docs/DEMO_STORYBOARD.md`** — canlı 6–8 dakikalık jüri demo senaryosu, an be an.
- **`http://localhost:8000/docs`** — backend ayaktayken otomatik üretilen OpenAPI explorer.
- **Kaynak kod** — yukarıdaki her yük-taşıyan modül kasıtlı olarak 300 satırın altında tutuldu, geleceğin bakımcısının tahmin etmek zorunda kalacağı yerlerde inline gerekçe yorumlarıyla.

---

## Lisans ve Teşekkürler

Eğitim / hackathon kullanımı. Üretim lisans şartları daha sonra.

48 saatte inşa edildi. 9-ajan demo işi, rayları göstermek için bir araç; rayların kendisi, katkıdır.

---

## Kapanış argümanı

Ajan ekonomisi gerçek, büyük, hızlanıyor ve **finansal olarak hizmetsiz**. Her yerleşik ödeme rayı, karşı tarafların yasal kişiliği, kredi geçmişi ve ihtilaf rücusu olan insanlar veya işletmeler olduğu varsayımıyla inşa edildi. Ajanların hiçbiri yok.

Bu repository — kodda, uçtan uca, hash-zincirli bir denetim iziyle — eksik rayları **şu an** inşa edebileceğinizi öneriyor ve gösteriyor. Beş ilke. Bir açık pazaryeri. Günler değil, saniyelerde uzlaştırma. Kriptografik yapıyla denetlenebilirlik. Trafikle ölçeklenen bir güven oracle'ı.

Otonom AI emeği bir sonraki on yılın verimlilik devrimiyse, **o zaman bu, onu bankaya yatırılabilir hale getiren altyapıdır.**

48 saatte inşa ettik. 48 hafta nasıl görünür hayal edin.
