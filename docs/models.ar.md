# النماذج الأساسية

في قلب أساس ثلاث فئات بيانات بسيطة في `asas.core.models`: `Request` و`Response` و`Payload`.
لا تعرف هذه الفئات شيئًا عن `httpx` أو أي طبقة نقل بعينها — فهي اللغة المشتركة التي تتحدّث بها
كل الطبقات، وهذا تحديدًا ما يتيح استبدال [المحرّكات](engines.md) و
[استراتيجيات المصادقة](authentication.md) بحرّية.

```
دالة @get  →  Request  →  auth.apply()  →  engine.send()  →  Response  →  دالتك
```

## Request

الطلب المستقلّ عن النقل الذي تعدّله استراتيجيات المصادقة وترسله المحرّكات.

```python
@dataclass
class Request:
    method: str
    url: str
    params: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = {}
    payload: Optional[Payload] = None
    timeout: Optional[float] = None
```

| الحقل | المعنى |
| --- | --- |
| `method` | دالة HTTP، مثل `"GET"` |
| `url` | عنوان URL المبني بالكامل (`base_url` + المسار المُحلّ) |
| `params` | وسائط الاستعلام |
| `headers` | ترويسات الطلب — حيث تكتب معظم استراتيجيات المصادقة |
| `payload` | جسم الطلب، إن وُجد (راجع `Payload` أدناه) |
| `timeout` | مهلة اختيارية لكل طلب |

تتلقّى دالة `Auth.apply` كائن `Request`، وتعدّل `headers` أو `params` فيه، ثم تعيده.

## Response

الاستجابة المستقلّة عن النقل التي ينتجها محرّكك وتستهلكها دالتك.

```python
@dataclass
class Response:
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str

    def json(self) -> Any:
        ...
```

| العضو | المعنى |
| --- | --- |
| `status_code` | رمز حالة HTTP |
| `headers` | ترويسات الاستجابة |
| `content` | جسم الاستجابة الخام بصيغة `bytes` |
| `text` | جسم الاستجابة مُفكّك الترميز إلى `str` |
| `json()` | تحليل `content` بوصفه JSON |

عندما لا تملك نقطة النهاية `response_model`، يكون هذا `Response` هو ما يحقنه أساس بوصفه الوسيط
الأول لدالتك — استدعِ `response.json()` لقراءة الجسم.

## Payload

حاوية عامة لبيانات الطلب، محمولة على `Request.payload`.

```python
@dataclass
class Payload:
    data: Optional[Any] = None
    json: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = {}
```

| الحقل | المعنى |
| --- | --- |
| `data` | جسم خام / مُرمَّز بصيغة نموذج |
| `json` | جسم JSON — وهو ما تُسلسَل إليه نماذج Pydantic |
| `files` | رفع الملفّات |
| `headers` | ترويسات خاصة بالجسم |

عندما تمرّر نموذج Pydantic إلى نقطة نهاية، يُسلسله أساس ويخزّن الناتج في `Payload.json`. راجع
[أجسام الطلب والاستجابات](request-response.md) لمعرفة كيفية عمل هذا التوجيه.

!!! note "نادرًا ما تبني هذه بنفسك"
    يبني أساس `Request` و`Payload` نيابةً عنك من استدعاء دالتك، وتبني المحرّكات `Response`.
    تتعامل مع هذه الأنواع مباشرةً بصورة رئيسية عند كتابة
    [محرّك مخصّص](engines.md) أو [استراتيجية مصادقة مخصّصة](authentication.md).
