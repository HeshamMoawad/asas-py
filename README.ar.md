
<p align="center">
  <a href="https://asas.dev"><img src="https://heshammoawad.github.io/asas-py/assets/logo-without-bg.png" alt="أساس"></a>
</p>

<p align="center">
    <em>إطار عمل أساس، أداء عالٍ، سهل التعلم، سريع البرمجة، جاهز للإنتاج</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/asas-py/"><img src="https://img.shields.io/pypi/v/asas-py" alt="إصدار PyPI"></a>
  <a href="https://pypi.org/project/asas-py/"><img src="https://img.shields.io/pypi/pyversions/asas-py" alt="إصدارات بايثون"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="الرخصة"></a>
</p>

---

> **أساس** هو إطار عمل بلغة بايثون لبناء **عملاء واجهات برمجة تطبيقات موجّهين ببساطة** في أسطر
> قليلة. تكتب صنفًا فرعيًا، وتُعلِّم الدوال بـ `@get`/`@post`/…، ويتولّى أساس بناء الطلب وتوجيه
> المعاملات والتحقق عبر Pydantic والمصادقة وإعادة المحاولة بعد التحديث والصفحات نيابةً عنك —
> للكود المتزامن **وغير المتزامن** باستخدام المزخرفات نفسها.

## لماذا أساس؟

تغرق مكتبات HTTP التقليدية شكل واجهتك البرمجية في كومة من استدعاءات `requests.get(...)`
وسلاسل الروابط ومعالجة JSON يدويًا. يقلب أساس المعادلة: **صنف العميل الخاص بك هو عميلك
البرمجي**، تُعلنه مرّة واحدة وتكتبه من البداية إلى النهاية.

- اكتب عميلك البرمجي بالكامل كصنف مع مزخرفات — لا رمزًا روتينيًا تحتاج صيانته.
- توقيع واحد يقود **أجزاء المسار ومعاملات الاستعلام والترويسات والكوكيز والنماذج والملفات
  وأجسام JSON** — بالاستنتاج، أو صراحةً بعلامات `Annotated`.
- **Pydantic يدخل، وPydantic مُتحقَّق منها يخرج.** تعليق نوع القيمة المُعادة هو نموذج الاستجابة،
  فيكون `client.get_user(1)` من النوع `User` لدى mypy ومحرّرك.
- **أخطاء مكتوبة الأنواع وخطافات**: الاستجابات غير 2xx ترفع `NotFoundError` و`RateLimitError`
  …، ويمكن مراقبة كل طلب عبر الخطافات.
- جاهز لواجهات حقيقية: مصادقة، تحديث تلقائي للرمز المميّز (حتى عند شروط مخصّصة)، وCRUD للموارد
  مع ترقيم صفحات لا يحتاج أي كود حلقة.

## التثبيت

```bash
pip install asas-py             # + Pydantic + httpx (the default engine)
pip install "asas-py[requests]" # + the optional sync-only requests engine
```

بايثون 3.10+ (انظر [التوثيق](#التوثيق) للدليل العربي).

## البداية السريعة

ورّث عميلًا وصرّح بنقاط النهاية. هذا كل شيء.

```python
from pydantic import BaseModel

from asas import AsasClient, get


class Todo(BaseModel):
    id: int
    todo: str
    completed: bool


class TodoClient(AsasClient):
    @get("/todos/{id}")
    def get_todo(self, id: int) -> Todo: ...


with TodoClient(base_url="https://dummyjson.com") as client:
    task = client.get_todo(1)       # typed: Todo
    print(task.todo)
```

`id` هو موضع في المسار، وتعليق نوع القيمة المُعادة `Todo` يتحقق من استجابة JSON. جسم الدالة لا
يُنفَّذ أبدًا، لذا فهو مجرد `...`. تريد غير المتزامن؟ استخدم `async def`
مع `AsasAsyncClient` — المزخرفات متطابقة. يعمل هذا المقطع كما هو ضد
[dummyjson.com](https://dummyjson.com) (واجهة REST عامة مجانية).

### جرّبه مباشرة

```python
from typing import List

from pydantic import BaseModel

from asas import AsasClient, get


class Product(BaseModel):
    id: int
    title: str
    price: float


class ProductPage(BaseModel):
    products: List[Product]


class StoreClient(AsasClient):
    @get("/products")
    def products(self) -> ProductPage: ...

    def product_list(self) -> List[Product]:
        return self.products().products


client = StoreClient(base_url="https://dummyjson.com")
first = client.product_list()
print(f"{len(first)} products, first: {first[0].title} (${first[0].price})")
```

### الموارد والترقيم الصفحي الكسول — دون كود حلقة صفحات

```python
from pydantic import BaseModel

from asas import AsasClient, AsasResource, OffsetPaginator


class User(BaseModel):
    id: int
    name: str


class Users(AsasResource[User]):
    path = "/users"
    paginator = OffsetPaginator(limit=100, items_key="users")


class Client(AsasClient):
    users = Users()


client = Client(base_url="https://api.example.com")
for user in client.users:          # pages fetched on demand, loop ends itself
    print(user.name)

single = client.users.get(42)      # generated CRUD, too: typed as User
```

### المعاملات والأخطاء والخطافات

```python
from typing import Annotated

from pydantic import BaseModel

from asas import AsasClient, Header, Hooks, NotFoundError, Query, get


class User(BaseModel):
    id: int
    name: str


class Users(AsasClient):
    @get("/users/{id}")
    def get_user(
        self,
        id: int,
        expand: Annotated[str | None, Query(alias="x-expand")] = None,
        trace: Annotated[str | None, Header("X-Trace")] = None,
    ) -> User: ...


hooks = Hooks(on_response=[lambda req, res: print(req.method, req.url, res.status_code)])
with Users(base_url="https://api.example.com", hooks=hooks) as client:
    try:
        user = client.get_user(1, trace="abc")
    except NotFoundError:
        user = None
```

### المصادقة والتحديث التلقائي

```python
from asas import AsasClient, RefreshingBearerAuth, get, refresh_on_keyword

auth = RefreshingBearerAuth(
    "expired-token",
    refresh_callback=lambda: mint_new_token(),
    refresh_when=refresh_on_keyword("token_expired"),  # refresh on a 200, too
)


class MyClient(AsasClient):
    @get("/me")
    def me(self) -> dict: ...


client = MyClient(base_url="https://api.example.com", auth=auth)
```

## المزايا

- **عملاء متزامنون وغير متزامنون** يتشاركون المزخرفات نفسها
  `@get`/`@post`/`@put`/`@delete`/`@patch` — يكتشف أساس `async def` تلقائيًا.
- **نقاط نهاية مكتوبة الأنواع** — تعليق نوع القيمة المُعادة يقود التحليل، فيرى المستدعون
  التوقيع الذي صرّحت به تمامًا (`assert_type(client.get_user(1), User)` ينجح تحت
  `mypy --strict`).
- **توجيه المعاملات** — مواضع في المسار، وأجسام Pydantic، ومعاملات استعلام تُستنتج من توقيع
  دالة واحد، أو صراحةً بعلامات `Path` / `Query` / `Header` / `Cookie` / `Body` / `Form` /
  `File` وأسماء مستعارة.
- **أخطاء مكتوبة الأنواع** — الاستجابات غير 2xx ترفع `NotFoundError` و`RateLimitError` …
  (كلها `AsasError`)، إضافةً إلى `ResponseValidationError` و`TransportError`.
- **الخطافات** — `on_request` / `on_response` / `on_error` على العميل أو نقطة النهاية.
- **الموارد + الترقيم الصفحي الكسول** — يمنحك `AsasResource[User]` العامّ دوال
  `list`/`get`/`create`/`update`/`delete` وترقيمًا بأسلوب المُكرِّر (استراتيجيات رقم الصفحة
  والإزاحة والمؤشّر ورابط رأس Link).
- **مصادقة جاهزة** — `NoAuth` و`BasicAuth` و`BearerAuth` و`APIKeyAuth` (ترويسة/استعلام/كوكي)
  و`RefreshingBearerAuth` و`CompositeAuth`، مع مصادقة قابلة للتبديل أثناء التشغيل وشروط
  تحديث سهلة الاختبار.
- **نواة مستقلّة عن النقل** — `httpx` مرفق؛ ويمكنك إحضار محرّكك الخاص (وهناك محرّك `requests`
  اختياري متزامن فقط خلف إضافة `[requests]`).

## خارطة الطريق

المزايا القادمة المخططة والتي تستحق المشاركة:

- [ ] **توليد عميل من OpenAPI / Swagger** — توليد عميل مكتوب بالكامل (نماذج Pydantic + كود
      العميل) مباشرةً من مخطط OpenAPI.
- [ ] **دعم GraphQL** — مزخرفات استعلام / تعديل / اشتراك مع استجابات مكتوبة.
- [ ] **وحدة اختبار** — أدوات مساعدة ومهايئات لجعل كتابة اختبارات العميل أمرًا يسيرًا (محاكاة
      respx وحوامل أساسية وطلبات مُلتقطة).
- [ ] **وسطاء وإعادة محاولات** — إعادة المحاولة/التراجع وخطافات غير متزامنة (الخطافات المتزامنة
      لدورة الحياة صدرت في 0.2).
- [ ] **أدوات الكوكيز والجلسات** — إدارة جلسات من الدرجة الأولى وأوعية كوكيز ومعالجة CSRF.

> لديك ميزة في ذهنك؟ [افتح قضية](https://github.com/heshammoawad/asas-py/issues) أو ابدأ
> نقاشًا — المساهمات والأفكار مرحّب بها جدًا.

## المساهمة

المساهمات من جميع الأنواع مرحّب بها — تقارير الأخطاء والتوثيق والأمثلة والمزايا.

1. **انشئ fork واستنسِخ** المستودع.
2. **جهّز البيئة:** `make dev-install` (يثبّت الاعتماديات وخطافات git).
3. **طوّر:** اكتب الكود مع تلميحات الأنواع، ثم شغّل `make format` و`make lint`.
4. **اختبر:** `make test`.
5. **التزم** برسالة واضحة وافتح **طلب سحب (PR)**.

انظر [CONTRIBUTING.md](CONTRIBUTING.md) لسير العمل الكامل ومعايير البرمجة.

## التوثيق

التوثيق الكامل (إنجليزي + عربي): [asas.dev](https://asas.dev) أو
[heshammoawad.github.io/asas-py](https://heshammoawad.github.io/asas-py/)

- [العملاء](docs/clients.ar.md)
- [التوجيه](docs/routing.ar.md)
- [الوسائط](docs/parameters.ar.md)
- [أجسام الطلبات والاستجابات](docs/request-response.ar.md)
- [الأخطاء](docs/errors.ar.md)
- [الخطافات](docs/hooks.ar.md)
- [الموارد والترقيم الصفحي](docs/resources.ar.md)
- [المصادقة](docs/authentication.ar.md)
- [المحرّكات وطبقات النقل](docs/engines.ar.md)
- [النماذج الأساسية](docs/models.ar.md)
- [الترقية إلى 0.2](docs/migration-0.2.ar.md)

## الرخصة

صدر تحت [رخصة MIT](LICENSE).
