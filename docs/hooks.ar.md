# الخطافات

تتيح لك الخطافات (hooks) مراقبة كل طلب واستجابة وخطأ أو تعديله دون لمس كل نقطة نهاية: التسجيل
وترويسات التتبّع والمقاييس وغيرها. وهي دوال عادية متزامنة تُجمَع في فئة البيانات `Hooks`.

```python
from collections.abc import Callable
from dataclasses import dataclass, field

from asas import AsasError, Request, Response


@dataclass
class Hooks:
    on_request: list[Callable[[Request], Request | None]] = field(default_factory=list)
    on_response: list[Callable[[Request, Response], None]] = field(default_factory=list)
    on_error: list[Callable[[AsasError], None]] = field(default_factory=list)
```

| قائمة الخطافات | التوقيع | الغرض |
| --- | --- | --- |
| `on_request` | `(Request) -> Request \| None` | عدّل الطلب وأعد `None`، أو أعد بديلًا |
| `on_response` | `(Request, Response) -> None` | راقب كل استجابة |
| `on_error` | `(AsasError) -> None` | راقب خطأً قبل رفعه |

## إرفاق الخطافات

مرّر الخطافات إلى العميل، أو إلى نقطة نهاية، أو إلى كليهما:

```python
import logging

from asas import AsasClient, AsasError, Hooks, Request, Response, get

log = logging.getLogger("api")


def stamp(request: Request) -> None:
    request.headers["X-Client"] = "asas-demo"


def log_response(request: Request, response: Response) -> None:
    log.info("%s %s -> %s", request.method, request.url, response.status_code)


def log_error(error: AsasError) -> None:
    log.warning("request failed: %s", error)


class Api(AsasClient):
    @get("/ping", hooks=Hooks(on_response=[lambda req, res: log.debug("ping")]))
    def ping(self) -> dict: ...


client = Api(
    base_url="https://api.example.com",
    hooks=Hooks(on_request=[stamp], on_response=[log_response], on_error=[log_error]),
)
```

`client.hooks` خاصية عامة، فيمكنك الإضافة إليها لاحقًا:
`client.hooks.on_request.append(stamp)`.

## الترتيب

في كل قائمة، **تعمل خطافات العميل أولًا ثم خطافات نقطة النهاية**، كلٌّ بترتيب ورودها في
القائمة. وعندما تتسلسل خطافات `on_request`، يستقبل كلٌّ منها الطلب الذي أنتجه سابقه.

```python
from asas import Hooks, Request


def add_trace(request: Request) -> Request | None:
    request.headers["X-Trace"] = "1"      # mutate and return None...
    return None


def replace(request: Request) -> Request | None:
    return Request(method="GET", url=request.url)   # ...or return a replacement


hooks = Hooks(on_request=[add_trace, replace])
```

## أين تعمل الخطافات في خط المعالجة

```
build request → auth.apply (if use_auth) → on_request* → engine.send → on_response*
    → on a 401 refresh / challenge: rebuild → auth.apply → on_request* → send → on_response*
      (exactly once)
    → status check   (HTTPStatusError)
    → parse response (ResponseValidationError)
    → return

TransportError, HTTPStatusError, ResponseValidationError  →  on_error*  →  raise
```

- يعمل `on_request` بعد تطبيق المصادقة، فترى الخطافات الترويسات النهائية. وعند إعادة محاولة
  التجديد أو التحدّي يُعاد بناء الطلب، ويعمل `on_request` و`on_response` مرّة أخرى.
- `on_error` للمراقبة فقط. يعمل **قبل** رفع الخطأ ولا يستطيع منعه. ولا يُطلَق إلا لأخطاء
  `TransportError` و`HTTPStatusError` و`ResponseValidationError` التي يرفعها خط المعالجة. ونقطة
  النهاية `-> Response` لا ترفع خطأً بسبب حالة HTTP أبدًا، لذا لا يُستدعى `on_error` للحالة
  هناك؛ أما `TransportError` فيبقى يُرفع ويُطلق `on_error`.
- الاستثناء المرفوع **داخل خطّاف** ينتشر كما هو، ولا يُستدعى `on_error` له.
- تمرّ الموارد (`AsasResource`) عبر خط المعالجة نفسه، فتنطبق خطافات العميل على طلبات CRUD
  والترقيم الصفحي لديها أيضًا.

## يجب ألّا تحجب الخطافات

الخطافات دوال متزامنة، وتخدم الخطافات نفسها العميل المتزامن وغير المتزامن. وفي
`AsasAsyncClient` تعمل على حلقة الأحداث، لذا يجب **ألّا تحجب على الإدخال/الإخراج** (لا نداءات
شبكة ولا قراءة ملفات ولا `time.sleep`). اجعلها سريعة: سجّل، أو اضبط ترويسة، أو زد عدّادًا.
الخطافات غير المتزامنة غير مدعومة في 0.2.
