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
| `OAuth2ClientCredentialsAuth` | منح OAuth2 ببيانات اعتماد العميل |
| `DigestAuth` | مصادقة HTTP Digest بالتحدّي/الاستجابة |
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

## OAuth2ClientCredentialsAuth

تطبّق منح OAuth2 **ببيانات اعتماد العميل** (client-credentials). تسكّ رمزًا حاملًا من نقطة
نهاية الرمز لديك وتجدّده عند `401`. يُطلق أول نداء محمي طلبَ الرمز تلقائيًا.

```python
from asas import AsasClient, OAuth2ClientCredentialsAuth

auth = OAuth2ClientCredentialsAuth(
    token_url="https://auth.example.com/oauth/token",
    client_id="my-client-id",
    client_secret="my-client-secret",
    scope="read write",   # اختياري
)
client = AsasClient(base_url="https://api.example.com", auth=auth)
```

افتراضيًا يُنفَّذ طلب الرمز بـ `httpx` (طلب `POST` لـ `grant_type=client_credentials`).
لتوجيهه عبر طبقة نقل مختلفة، مرِّر `token_fetcher` (متزامن) أو `async_token_fetcher` (غير
متزامن). يتلقّى كلٌّ منهما حقول النموذج ويعيد إمّا سلسلة رمز الوصول أو قاموسًا بالشكل
`{"access_token": ..., "expires_in": ...}`:

```python
def fetch(form: dict) -> dict:
    resp = my_http_lib.post("https://auth.example.com/oauth/token", data=form)
    return resp.json()   # {"access_token": "...", "expires_in": 3600}

auth = OAuth2ClientCredentialsAuth(
    token_url="https://auth.example.com/oauth/token",
    client_id="id",
    client_secret="secret",
    token_fetcher=fetch,
)
```

عندما تتضمّن استجابة الرمز `expires_in`، تعكس ذلك الخاصية `is_expired`.

## DigestAuth

مصادقة HTTP Digest (RFC 7616)، تُعالَج بالتحدّي/الاستجابة:

1. يُرسَل الطلب الأول **دون** بيانات اعتماد.
2. يردّ الخادم بـ `401` مع تحدٍّ `WWW-Authenticate: Digest …`.
3. يعيد أساس تغذية التحدّي إلى الاستراتيجية، ويعيد بناء الطلب بالملخّص (digest) المحسوب،
   ويعيد المحاولة مرّة واحدة.

```python
from asas import AsasClient, DigestAuth

auth = DigestAuth("username", "password")
client = AsasClient(base_url="https://api.example.com", auth=auth)
```

يدعم `qop=auth` وخوارزميتَي `MD5` و`SHA-256`. وتعيد الطلبات اللاحقة استخدام التحدّي المخزّن
مع عدّاد nonce متزايد.

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
  كي تتمكّن أنظمة مثل Digest من قراءة تحدّي الخادم قبل إعادة المحاولة.

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
