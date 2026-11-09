# العملاء

**العميل** هو الكائن الذي ترثه لوصف واجهة برمجة معيّنة. يحمل ثلاثة أشياء: عنوان الأساس
`base_url`، ومحرّك النقل `engine`، واستراتيجية مصادقة اختيارية `auth`. يوفّر أساس فئتين
أساسيتين جاهزتين.

| الفئة | الوضع | المحرّك الافتراضي |
| --- | --- | --- |
| `AsasClient` | متزامن | `HTTPXSyncEngine` |
| `AsasAsyncClient` | غير متزامن | `HTTPXAsyncEngine` |

## تعريف عميل

ورِث الفئة الأساسية المناسبة لأسلوب كودك وأضف دوالًا مزخرفة. استخدام العميل كمدير سياق
(context manager) يغلقه نيابةً عنك:

=== "متزامن"

    ```python
    from pydantic import BaseModel

    from asas import AsasClient, get


    class GitHubUser(BaseModel):
        login: str
        id: int


    class GitHubClient(AsasClient):
        @get("/users/{username}")
        def get_user(self, username: str) -> GitHubUser: ...


    with GitHubClient(base_url="https://api.github.com") as client:
        user = client.get_user("torvalds")
    ```

=== "غير متزامن"

    ```python
    from pydantic import BaseModel

    from asas import AsasAsyncClient, get


    class GitHubUser(BaseModel):
        login: str
        id: int


    class GitHubClient(AsasAsyncClient):
        @get("/users/{username}")
        async def get_user(self, username: str) -> GitHubUser: ...


    async def main() -> None:
        async with GitHubClient(base_url="https://api.github.com") as client:
            user = await client.get_user("torvalds")
    ```

## وسائط المُنشئ

يتشارك العميلان التوقيع نفسه. كل ما بعد `base_url` **مفتاحي فقط**:

```python
def __init__(
    self,
    base_url="",
    *,
    engine=None,
    auth=None,
    hooks=None,
    raise_for_status=True,
    **engine_kwargs,
): ...
```

- **`base_url`** — البادئة التي تُدمج مع كل مسار مزخرف. تُحذف الشرطة المائلة الأخيرة، لذا فإن
  `https://api.example.com` و`https://api.example.com/` متطابقان في السلوك.
- **`engine`** — طبقة نقل تطبّق بروتوكول المحرّك. الافتراضي هو محرّك `httpx` المرفق. راجع
  [المحرّكات وطبقات النقل](engines.md).
- **`auth`** — استراتيجية مصادقة اختيارية. راجع [المصادقة](authentication.md).
- **`hooks`** — نسخة [`Hooks`](hooks.md) اختيارية. وهي متاحة أيضًا كالخاصية العامة
  `client.hooks`.
- **`raise_for_status`** — هل ترفع الاستجابات غير 2xx [خطأً مكتوب النوع](errors.md). يمكن
  لنقاط النهاية تجاوزه. الافتراضي `True`.
- **`**engine_kwargs`** — أي وسائط مفتاحية إضافية تُمرَّر إلى مُنشئ عميل `httpx` الأساسي (عند
  استخدام المحرّك الافتراضي).

```python
# Extra kwargs flow straight through to httpx.Client / httpx.AsyncClient
client = GitHubClient(
    base_url="https://api.github.com",
    timeout=10.0,
    headers={"Accept": "application/vnd.github+json"},
)
```

يطبّق المحرّك الافتراضي إعدادات العميل هذه على كل طلب: فـ `headers` و`timeout` وغيرها مما تمرّره
هنا يصبح نافذًا، وتُطبَّق فوقها القيم الخاصة بكل نقطة نهاية (`timeout=` و`headers=`).

!!! note "المحرّكات المخصّصة تتجاهل `**engine_kwargs`"
    تمرير الوسائط ينطبق فقط عندما ينشئ أساس محرّك `httpx` الافتراضي. إذا مرّرت محرّكك
    الخاص عبر `engine=`، فاضبط ذلك المحرّك مباشرةً بدلًا من ذلك.

## تبديل المصادقة أثناء التشغيل

`auth` خاصية قابلة للضبط، فيمكنك تغيير بيانات الاعتماد بعد الإنشاء — على سبيل المثال مباشرةً
بعد أن يُعيد نداء تسجيل الدخول رمزًا (token):

```python
from asas import AsasClient, BearerAuth, post
from pydantic import BaseModel

class Credentials(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    token: str

class ApiClient(AsasClient):
    @post("/auth/login", use_auth=False)
    def login(self, credentials: Credentials) -> Token: ...

client = ApiClient(base_url="https://api.example.com")

# 1. Authenticate without any auth header...
data = client.login(Credentials(username="ada", password="secret"))

# 2. ...then attach the returned token for every subsequent call.
client.auth = BearerAuth(data.token)
```

ضبط `client.auth = None` يزيل المصادقة بالكامل.

## إغلاق العميل

تُبقي طبقة النقل تجمّع اتصالات مفتوحًا. أبسط طريقة لتحريره هي مدير سياق، فهو يغلق العميل عند
الخروج حتى لو رفعت الكتلة استثناءً:

=== "متزامن"

    ```python
    with GitHubClient(base_url="https://api.github.com") as client:
        client.get_user("torvalds")
    # closed here
    ```

=== "غير متزامن"

    ```python
    async def main() -> None:
        async with GitHubClient(base_url="https://api.github.com") as client:
            await client.get_user("torvalds")
        # closed here
    ```

وبدون مدير سياق، استدعِ `client.close()` (متزامن) أو `await client.aclose()` (غير متزامن).

!!! warning "إغلاق العميل يغلق محرّكه"
    يغلق العميل محرّكه دائمًا، **حتى لو كان محرّكًا مرّرته أنت**. إن شاركت محرّكًا واحدًا بين
    عدّة عملاء، فإغلاق أي منهم يغلقه للجميع. في هذه الحالة أدِر عمر المحرّك بنفسك: أغلق المحرّك
    مباشرةً (`engine.close()` / `await engine.aclose()`) عند انتهاء آخر عميل، ولا تستخدم
    العملاء كمديري سياق.
