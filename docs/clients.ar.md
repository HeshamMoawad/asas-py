# العملاء

**العميل** هو الكائن الذي ترثه لوصف واجهة برمجة معيّنة. يحمل ثلاثة أشياء: عنوان الأساس
`base_url`، ومحرّك النقل `engine`، واستراتيجية مصادقة اختيارية `auth`. يوفّر أساس فئتين
أساسيتين جاهزتين.

| الفئة | الوضع | المحرّك الافتراضي |
| --- | --- | --- |
| `AsasClient` | متزامن | `HTTPXSyncEngine` |
| `AsasAsyncClient` | غير متزامن | `HTTPXAsyncEngine` |

## تعريف عميل

ورِث الفئة الأساسية المناسبة لأسلوب كودك وأضف دوالًا مزخرفة:

=== "متزامن"

    ```python
    from asas import AsasClient, get, Response

    class GitHubClient(AsasClient):
        @get("/users/{username}")
        def get_user(self, response: Response, username: str):
            return response.json()

    client = GitHubClient(base_url="https://api.github.com")
    user = client.get_user(username="torvalds")
    ```

=== "غير متزامن"

    ```python
    from asas import AsasAsyncClient, get, Response

    class GitHubClient(AsasAsyncClient):
        @get("/users/{username}")
        async def get_user(self, response: Response, username: str):
            return response.json()

    async def main():
        client = GitHubClient(base_url="https://api.github.com")
        user = await client.get_user(username="torvalds")
        await client.engine.aclose()
    ```

## وسائط المُنشئ

يتشارك العميلان التوقيع نفسه:

```python
AsasClient(base_url="", engine=None, auth=None, **kwargs)
```

- **`base_url`** — البادئة التي تُدمج مع كل مسار مزخرف. تُحذف الشرطة المائلة الأخيرة، لذا فإن
  `https://api.example.com` و`https://api.example.com/` متطابقان في السلوك.
- **`engine`** — طبقة نقل تطبّق بروتوكول المحرّك. الافتراضي هو محرّك `httpx` المرفق. راجع
  [المحرّكات وطبقات النقل](engines.md).
- **`auth`** — استراتيجية مصادقة اختيارية. راجع [المصادقة](authentication.md).
- **`**kwargs`** — أي وسائط مفتاحية إضافية تُمرَّر إلى مُنشئ عميل `httpx` الأساسي (عند استخدام
  المحرّك الافتراضي).

```python
# الوسائط الإضافية تُمرَّر مباشرةً إلى httpx.Client / httpx.AsyncClient
client = GitHubClient(
    base_url="https://api.github.com",
    timeout=10.0,
    headers={"Accept": "application/vnd.github+json"},
)
```

!!! note "المحرّكات المخصّصة تتجاهل `**kwargs`"
    تمرير `**kwargs` ينطبق فقط عندما ينشئ أساس محرّك `httpx` الافتراضي. إذا مرّرت محرّكك
    الخاص عبر `engine=`، فاضبط ذلك المحرّك مباشرةً بدلًا من ذلك.

## تبديل المصادقة أثناء التشغيل

`auth` خاصية قابلة للضبط، فيمكنك تغيير بيانات الاعتماد بعد الإنشاء — على سبيل المثال مباشرةً
بعد أن يُعيد نداء تسجيل الدخول رمزًا (token):

```python
from asas import AsasClient, BearerAuth, post, Response
from pydantic import BaseModel

class Credentials(BaseModel):
    username: str
    password: str

class ApiClient(AsasClient):
    @post("/auth/login", use_auth=False)
    def login(self, response: Response, credentials: Credentials):
        return response.json()

client = ApiClient(base_url="https://api.example.com")

# 1. سجّل الدخول دون أي ترويسة مصادقة...
data = client.login(credentials=Credentials(username="ada", password="secret"))

# 2. ...ثم أرفق الرمز المُعاد لكل نداء لاحق.
client.auth = BearerAuth(data["token"])
```

ضبط `client.auth = None` يزيل المصادقة بالكامل.

## إغلاق العميل

تُبقي طبقة النقل تجمّع اتصالات مفتوحًا. أغلقه عند الانتهاء — خاصةً للعميل غير المتزامن الذي
يجب انتظاره بـ `await`:

=== "متزامن"

    ```python
    client.engine.close()
    ```

=== "غير متزامن"

    ```python
    await client.engine.aclose()
    ```
