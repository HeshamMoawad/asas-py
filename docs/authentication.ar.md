# المصادقة

المصادقة في أساس كائن استراتيجية صغير قابل للاستبدال. تمرّر واحدًا عبر `auth=` عند إنشاء
العميل، فيُطبَّق على كل طلب (ما لم تنسحب نقطة نهاية عبر
[`use_auth=False`](routing.md)).

```python
from asas import AsasClient, BearerAuth

client = AsasClient(base_url="https://api.example.com", auth=BearerAuth("token"))
```

## الاستراتيجيات في لمحة

| الاستراتيجية | استخدمها لـ |
| --- | --- |
| `NoAuth` | استراتيجية صريحة بلا بيانات اعتماد |
| `BasicAuth` | مصادقة HTTP الأساسية (`Authorization: Basic …`) |
| `BearerAuth` | رمز حامل ثابت |
| `APIKeyAuth` | مفتاح API في ترويسة أو استعلام أو كوكي |
| `RefreshingBearerAuth` | رمز حامل يتجدّد عند `401` |
| `CompositeAuth` | الجمع بين عدّة استراتيجيات معًا |

## NoAuth

استراتيجية لا تفعل شيئًا. مفيدة بوصفها بديلًا واضحًا ومقصودًا عن `auth=None`.

```python
from asas import AsasClient, NoAuth

client = AsasClient(base_url="https://api.example.com", auth=NoAuth())
```

## BasicAuth

مصادقة HTTP الأساسية. تُرمِّز `username:password` وتضبط ترويسة `Authorization`.

```python
from asas import BasicAuth

auth = BasicAuth("username", "password")
# -> Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```

## BearerAuth

رمز حامل ثابت.

```python
from asas import BearerAuth

auth = BearerAuth("my-secret-token")
# -> Authorization: Bearer my-secret-token
```

## APIKeyAuth

مفتاح API يُرسَل في ترويسة (الافتراضي) أو سلسلة استعلام أو كوكي. يُختار الموضع عبر التعداد
`APIKeyLocation`؛ كما تُقبل سلسلة نصية بسيطة `"header"` / `"query"` / `"cookie"`.

=== "ترويسة (الافتراضي)"

    ```python
    from asas import APIKeyAuth

    auth = APIKeyAuth("secret-key", name="X-API-Key")
    # -> X-API-Key: secret-key
    ```

=== "سلسلة استعلام"

    ```python
    from asas import APIKeyAuth, APIKeyLocation

    auth = APIKeyAuth("secret-key", name="api_key", location=APIKeyLocation.QUERY)
    # -> ...?api_key=secret-key
    ```

=== "كوكي"

    ```python
    from asas import APIKeyAuth, APIKeyLocation

    auth = APIKeyAuth("secret-key", name="session", location=APIKeyLocation.COOKIE)
    # -> Cookie: session=secret-key
    ```

يحوي `APIKeyLocation` ثلاثة أعضاء: `HEADER` و`QUERY` و`COOKIE`. تمرير سلسلة موضع غير معروفة
يرفع `ValueError`.

## RefreshingBearerAuth

رمز حامل **يجدّد نفسه عند `401`**. عندما تعود استجابة غير مصرّح بها، يستدعي أساس نداء التجديد
لديك، ويعيد بناء الطلب بالرمز الجديد، ويعيد المحاولة **مرّة واحدة بالضبط**.

=== "متزامن"

    ```python
    from asas import AsasClient, RefreshingBearerAuth

    def fetch_new_token() -> str:
        # نادِ خادم المصادقة هنا وأعد الرمز الجديد.
        return "new-token"

    auth = RefreshingBearerAuth("initial-token", refresh_callback=fetch_new_token)
    client = AsasClient(base_url="https://api.example.com", auth=auth)
    ```

=== "غير متزامن"

    ```python
    from asas import AsasAsyncClient, RefreshingBearerAuth

    async def fetch_new_token() -> str:
        return "new-token"

    auth = RefreshingBearerAuth("initial-token", async_refresh_callback=fetch_new_token)
    client = AsasAsyncClient(base_url="https://api.example.com", auth=auth)
    ```

يمكنك تخصيص الترويسة والبادئة عبر `key_name=` و`token_prefix=` (الافتراضيان:
`"Authorization"` و`"Bearer "`).

!!! note "حدّ إعادة المحاولة"
    يحدث التجديد وإعادة المحاولة مرّة واحدة على الأكثر لكل نداء. وإذا عاد الطلب المُعاد بـ
    `401` أيضًا، تُعاد تلك الاستجابة كما هي.

## تخصيص متى يحدث التجديد

افتراضيًا لا يحدث التجديد إلّا عند `401` من HTTP. لكن كثيرًا من الواجهات تشير إلى انتهاء
صلاحية الرمز بطريقة مختلفة — استجابة `200` تحمل رمز خطأ في الجسم، أو كلمة مفتاحية في الحمولة،
أو رمز حالة غير قياسي. مرِّر شرط `refresh_when` لتجاوز *متى* يُنفَّذ التجديد وإعادة المحاولة.
يعمل هذا مع `RefreshingBearerAuth`.

الشرط ما هو إلّا `Callable[[Response], bool]`. ويوفّر أساس بُناةً للحالات الشائعة (استوردها من
`asas`):

| الباني | يُجدّد عندما… |
| --- | --- |
| `refresh_on_status(*codes)` | تكون الحالة إحدى `codes` (الافتراضي `401`) |
| `refresh_on_keyword(keyword)` | تظهر `keyword` في أي مكان من جسم الاستجابة |
| `refresh_on_json(key, value=…, status=…)` | يحوي جسم JSON المفتاح `key` (واختياريًا `== value`، واختياريًا عند حالة معيّنة) |
| `refresh_on_any(*conditions)` | يتحقّق أيّ من الشروط |
| `refresh_on_all(*conditions)` | تتحقّق كل الشروط |

=== "كلمة مفتاحية في الجسم"

    ```python
    from asas import RefreshingBearerAuth, refresh_on_keyword

    # جدّد عندما يحوي جسم الاستجابة "token_expired" (حتى مع 200).
    auth = RefreshingBearerAuth(
        "token",
        refresh_callback=get_new_token,
        refresh_when=refresh_on_keyword("token_expired"),
    )
    ```

=== "200 مع مفتاح/قيمة في الجسم"

    ```python
    from asas import RefreshingBearerAuth, refresh_on_json

    # جدّد عندما تردّ الواجهة 200 لكن الجسم يقول إن الرمز انتهى.
    auth = RefreshingBearerAuth(
        "token",
        refresh_callback=get_new_token,
        refresh_when=refresh_on_json("code", "AUTH_EXPIRED", status=200),
    )
    ```

=== "حالة مخصّصة"

    ```python
    from asas import RefreshingBearerAuth, refresh_on_status

    # بعض الواجهات تستخدم 419/440 لانتهاء الجلسة بدلًا من 401.
    auth = RefreshingBearerAuth(
        "token",
        refresh_callback=get_new_token,
        refresh_when=refresh_on_status(419, 440),
    )
    ```

=== "دمج الشروط"

    ```python
    from asas import RefreshingBearerAuth, refresh_on_any, refresh_on_status, refresh_on_keyword

    auth = RefreshingBearerAuth(
        "token",
        refresh_callback=get_new_token,
        refresh_when=refresh_on_any(refresh_on_status(401), refresh_on_keyword("expired")),
    )
    ```

يقبل `refresh_on_json` مفتاحًا منقّطًا `key` للأجسام المتداخلة (مثل `"error.code"`).

وللتحكّم الكامل، ورِث الاستراتيجية وتجاوز `should_refresh(response) -> bool`:

```python
class HeaderRefreshAuth(RefreshingBearerAuth):
    def should_refresh(self, response):
        # أسماء ترويسات الاستجابة بأحرف صغيرة.
        return response.headers.get("x-token-expired") == "1"
```

!!! note "استراتيجيات المصادقة المخصّصة لا تتأثّر"
    يُقرأ الشرط من دالة `should_refresh` اختيارية. أما الاستراتيجية التي تطبّق `refresh` /
    `arefresh` فقط فتحتفظ بسلوك `401` الافتراضي.

## CompositeAuth

طبّق عدّة استراتيجيات على طلب واحد بالترتيب — مفيد عندما تحتاج واجهة برمجة إلى أكثر من بيانات
اعتماد دفعةً واحدة (مثلًا مفتاح API **و** رمز حامل):

```python
from asas import AsasClient, CompositeAuth, APIKeyAuth, BearerAuth

auth = CompositeAuth(
    APIKeyAuth("key-123", name="X-API-Key"),
    BearerAuth("token-abc"),
)
client = AsasClient(base_url="https://api.example.com", auth=auth)
# -> X-API-Key: key-123  و  Authorization: Bearer token-abc
```

يُفوَّض التجديد ومعالجة التحدّي إلى أي أعضاء يدعمونهما، لذا يظل `CompositeAuth` الذي يحوي
`RefreshingBearerAuth` يجدّد عند `401`.

## كيف تُطبَّق المصادقة

تطبّق كل استراتيجية بروتوكول `Auth` — دالة واحدة `apply(request) -> request` تعدّل الترويسات
أو وسائط الاستعلام. ويوسّعه بروتوكولان:

- **`RefreshableAuth`** يضيف `refresh()` / `arefresh()`، يُستدعى عند `401` لتجديد بيانات
  الاعتماد قبل إعادة محاولة واحدة.
- **`ChallengeResponseAuth`** يضيف `handle_challenge(response) -> bool`، يُستدعى عند `401`
  كي تتمكّن الاستراتيجية من قراءة تحدّي الخادم قبل إعادة المحاولة.

لبناء نظامك الخاص، طبّق `apply` (واختياريًا أحد البروتوكولين أعلاه):

```python
from asas.auth import Auth
from asas.core.models import Request

class HeaderAuth(Auth):
    def __init__(self, header: str, value: str) -> None:
        self.header = header
        self.value = value

    def apply(self, request: Request) -> Request:
        request.headers[self.header] = self.value
        return request
```

راجع [النماذج الأساسية](models.md) لمعرفة شكل `Request` الذي تتلقّاه دالة `apply` لديك.
