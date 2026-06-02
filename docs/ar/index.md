# أساس (Asas)

<p align="center">
  <img src="../assets/logo-without-bg.png" alt="شعار أساس" width="300">
</p>

*إطار عمل أساس، أداء عالٍ، سهل التعلم، سريع البرمجة، جاهز للإنتاج*

---

## عن المشروع

أساس هو إطار عمل مبسط مصمم لبناء عملاء واجهة برمجة التطبيقات (API clients) من خلال واجهة نظيفة تعتمد على المزخرفات (decorators). تم تصميمه لتطوير بايثون الحديث، ويوفر دعماً أصيلاً للعمليات غير المتزامنة (asynchronous) وتكاملاً سلساً مع Pydantic للتحقق القوي من البيانات.

## الهدف

الهدف الأساسي لـ أساس هو إعادة تعريف تكامل واجهة برمجة التطبيقات من خلال جعلها أكثر "بايثونية" وأناقة وقابلية للصيانة. من خلال تجريد التفاصيل المملة المرتبطة عادةً بمكتبات الطلبات التقليدية، يمنح أساس المطورين القدرة على التركيز على البنية الواضحة والكود المعبر.

## البداية السريعة

### التثبيت

```bash
pip install asas-py
```

### الاستخدام

يوفر أساس عملاء منفصلين للعمليات المتزامنة وغير المتزامنة.

#### عميل متزامن (Synchronous Client)

```python
from asas import AsasClient, get, Response

class MyClient(AsasClient):
    @get("/users/{id}")
    def get_user(self, response: Response, id: int):
        return response.json()

client = MyClient(base_url="https://api.example.com")
user = client.get_user(id=1)
```

#### عميل غير متزامن (Asynchronous Client)

```python
from asas import AsasAsyncClient, get, Response

class MyAsyncClient(AsasAsyncClient):
    @get("/users/{id}")
    async def get_user(self, response: Response, id: int):
        return response.json()

async def main():
    client = MyAsyncClient(base_url="https://api.example.com")
    user = await client.get_user(id=1)
    await client.engine.aclose()
```

## الميزات

### المصادقة (Authentication)

يدعم أساس عدة استراتيجيات للمصادقة بشكل افتراضي:

- **BasicAuth**: `BasicAuth("username", "password")`
- **BearerAuth**: `BearerAuth("your-token")`
- **APIKeyAuth**: `APIKeyAuth("your-key", name="X-API-Key", location="header")` (يدعم `header` أو `query`)

```python
from asas import AsasClient, BearerAuth

auth = BearerAuth("my-secret-token")
client = MyClient(base_url="https://api.example.com", auth=auth)
```

### تحديث الرمز تلقائياً (Automatic Token Refresh)

يمكنك استخدام `RefreshingBearerAuth` لتحديث الرموز تلقائياً عند استلام استجابة `401 Unauthorized`.

```python
from asas import AsasAsyncClient, RefreshingBearerAuth

async def refresh_token():
    # المنطق الخاص بك للحصول على رمز جديد
    return "new-token"

auth = RefreshingBearerAuth(
    token="initial-token",
    async_refresh_callback=refresh_token
)

client = MyAsyncClient(base_url="https://api.example.com", auth=auth)
# إذا أعاد الطلب 401، فسيقوم بتحديث الرمز وإعادة المحاولة تلقائياً مرة واحدة.
```

### التحكم في المصادقة لكل نقطة نهاية (Per-Endpoint Auth Control)

تعطيل المصادقة لنقاط نهاية عامة محددة حتى لو كان العميل لديه استراتيجية مصادقة عامة.

```python
class MyClient(AsasClient):
    @get("/public-data", use_auth=False)
    def get_public(self, response: Response):
        return response.json()
```

### التكامل مع Pydantic

يتكامل أساس بسلاسة مع Pydantic للتحقق من صحة الطلبات والاستجابات.

```python
from pydantic import BaseModel
from typing import List

class User(BaseModel):
    id: int
    name: str

class MyClient(AsasClient):
    @get("/users", response_model=List[User])
    def get_users(self, users: List[User]):
        return users
```
