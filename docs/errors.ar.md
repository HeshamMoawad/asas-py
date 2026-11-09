# الأخطاء

كل خطأ يرفعه أساس يرث من `AsasError`، وكلها مُصدَّرة من مستوى الحزمة الأعلى. استجابة غير 2xx
ترفع افتراضيًا استثناءً مكتوب النوع، فلم يعد ممكنًا الخلط بين نداء فاشل وآخر ناجح.

## التسلسل الهرمي

```
AsasError
├── HTTPStatusError(request, response)          .status_code
│   ├── ClientError                              4xx fallback
│   │   ├── BadRequestError            400
│   │   ├── UnauthorizedError          401
│   │   ├── ForbiddenError             403
│   │   ├── NotFoundError              404
│   │   ├── ConflictError              409
│   │   ├── UnprocessableEntityError   422
│   │   └── RateLimitError             429      .retry_after: float | None
│   └── ServerError                              5xx fallback
│       ├── InternalServerError        500
│       └── ServiceUnavailableError    503
├── ResponseValidationError(response, error)    wraps pydantic / JSON errors
└── TransportError(message, request)            raised by engines, chained with `from`
```

- **`HTTPStatusError`** يملك `request` و`response` و`status_code`. يفوز الصنف الأكثر تحديدًا
  للحالة؛ وإلا فإن 4xx ترفع `ClientError`، و5xx ترفع `ServerError`، وأي حالة أخرى غير 2xx
  (1xx أو 3xx) ترفع `HTTPStatusError` نفسه.
- **`ResponseValidationError`** يملك `response` و`error`. يُرفع عندما لا يكون الجسم JSON صالحًا،
  أو لا يطابق نوع القيمة المُعادة، أو يكون فارغًا لنوع لا يقبل `None`.
- **`TransportError`** يملك `request`. ويعني أنه لم تُنتَج أي استجابة: فشل اتصال أو انتهاء
  مهلة وما إلى ذلك. ويُسلسَل الاستثناء الأصلي للمكتبة بوصفه `__cause__`.

تبدو رسالة خطأ الحالة هكذا:
`GET https://api.example.com/users/1 → 404 Not Found: <أول 200 حرف من الجسم>`.

## متى تُرفع الأخطاء

يُحسم رفع الخطأ عند حالة غير 2xx بالترتيب التالي:

1. وسيط `raise_for_status=` الخاص بنقطة النهاية، إن لم يكن `None`
2. قيمة `raise_for_status` للعميل (الافتراضي `True`)

```python
from pydantic import BaseModel

from asas import AsasClient, get


class User(BaseModel):
    id: int
    name: str


class Users(AsasClient):
    @get("/users/{id}")
    def get_user(self, id: int) -> User:
        raise NotImplementedError

    @get("/users/{id}/lenient", raise_for_status=False)
    def get_user_lenient(self, id: int) -> dict:
        raise NotImplementedError


strict = Users(base_url="https://api.example.com")
lenient = Users(base_url="https://api.example.com", raise_for_status=False)
```

تُرفع أخطاء الحالة **بعد** محاولة إعادة المحاولة الخاصة بتجديد المصادقة أو التحدّي. فالرمز
المنتهي الذي يتجدّد بنجاح لا يظهر أبدًا كـ `UnauthorizedError`؛ أما الذي يعيد `401` بعد
إعادة المحاولة الوحيدة فيظهر.

### الانسحاب عبر `-> Response`

نقطة النهاية المُعلَّقة بـ `-> Response` **لا ترفع خطأً بسبب الحالة أبدًا**، مهما كانت قيمة
`raise_for_status`، ولا تُستدعى خطافات `on_error` لها. استخدمها عندما تريد فحص الحالة بنفسك:

```python
from asas import AsasClient, Response, get


class Users(AsasClient):
    @get("/users/{id}")
    def probe(self, id: int) -> Response:
        raise NotImplementedError


client = Users(base_url="https://api.example.com")
response = client.probe(1)
if response.status_code == 404:
    print("no such user")
```

يبقى `TransportError` يُرفع لنقطة نهاية `-> Response`، لأنه لا توجد استجابة أصلًا.

## التقاط الأخطاء

التقط أكثر الأصناف تحديدًا مما تستطيع معالجته، ثم ارجع إلى صنف أوسع:

```python
from asas import (
    AsasError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TransportError,
)

try:
    user = client.get_user(1)
except NotFoundError:
    user = None
except RateLimitError as exc:
    wait = exc.retry_after   # seconds, or None
except ServerError as exc:
    print("server problem", exc.status_code)
except TransportError as exc:
    print("could not reach the server", exc.request.url)
except AsasError:
    raise
```

### قراءة `retry_after`

`RateLimitError.retry_after` هو عدد الثواني التي طلب الخادم أن تنتظرها. يحلّل أساس ترويسة
`Retry-After` بوصفها ثواني أو تاريخ HTTP (يُحوَّل إلى ثوانٍ من الآن، ولا يقل عن `0`). وتكون
`None` عندما تغيب الترويسة أو يتعذّر تحليلها.

```python
import time

from asas import RateLimitError

try:
    client.get_user(1)
except RateLimitError as exc:
    time.sleep(exc.retry_after or 1.0)
    client.get_user(1)
```

## كتابة محرّك يرفع `TransportError`

يجب على المحرّكات تغليف استثناءات النقل في مكتبتها داخل `TransportError`؛ راجع
[المحرّكات](engines.md).

## مراقبة الأخطاء

تستطيع [الخطافات](hooks.md) مراقبة كل خطأ قبل رفعه عبر `on_error`.
