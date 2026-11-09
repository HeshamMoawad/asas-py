# الترقية إلى 0.2

الإصدار 0.2.0 من أساس إصدار كاسر للتوافق. الفكرة الأساسية أن الدالة المزخرفة تُعرَّف الآن كدالة
مكتوبة الأنواع — **تعليق نوع القيمة المُعادة** يقود التحليل و**الوسائط** تقود الطلب — فيحصل
المستدعون على أنواع صحيحة. تعرض هذه الصفحة زوج «قبل/بعد» لكل تغيير كاسر.

## 1. أجسام نقاط النهاية لم تعد تستقبل النتيجة المُحلَّلة

في 0.1 كانت النتيجة المُحلَّلة تُحقَن بوصفها أول وسيط بعد `self`. في 0.2 لا يُحقَن شيء، ولا
يُنفَّذ الجسم أبدًا، ويحدّد تعليق نوع القيمة المُعادة ما تحصل عليه.

=== "0.1"

    ```python
    @get("/users/{id}", response_model=User)
    def get_user(self, user: User, id: int) -> User:
        return user

    client.get_user(id=1)
    ```

=== "0.2"

    ```python
    @get("/users/{id}")
    def get_user(self, id: int) -> User:
        raise NotImplementedError

    client.get_user(1)
    ```

لمعالجة نتيجة لاحقًا، اكتب دالة عادية تستدعي نقطة النهاية، أو استخدم [خطّافًا](hooks.md).
وللحصول على الاستجابة الخام علِّق النوع بـ `-> Response`.

=== "0.1"

    ```python
    @get("/users/{id}")
    def get_username(self, response: Response, id: int) -> str:
        return response.json()["name"]
    ```

=== "0.2"

    ```python
    @get("/users/{id}")
    def get_user(self, id: int) -> User:
        raise NotImplementedError

    def get_username(self, id: int) -> str:
        return self.get_user(id).name
    ```

اكتب `raise NotImplementedError` جسمًا للدالة: فـ `mypy --strict` يرفض `...` المجرّدة بالخطأ
`[empty-body]`.

## 2. حُذف `response_model=`

=== "0.1"

    ```python
    @get("/users", response_model=List[User])
    def get_users(self, users: List[User]) -> List[User]:
        return users
    ```

=== "0.2"

    ```python
    @get("/users")
    def get_users(self) -> list[User]:
        raise NotImplementedError
    ```

غياب تعليق نوع القيمة المُعادة يرفع `TypeError`.

## 3. الاستجابات غير 2xx ترفع خطأً افتراضيًا

=== "0.1"

    ```python
    data = client.get_user(id=404)      # returned the error body, silently
    ```

=== "0.2"

    ```python
    from asas import NotFoundError

    try:
        user = client.get_user(404)
    except NotFoundError:
        user = None
    ```

للانسحاب: على مستوى العميل عبر `AsasClient(raise_for_status=False)`، أو على مستوى نقطة النهاية
عبر `@get(..., raise_for_status=False)`، أو بإعادة `Response`. راجع [الأخطاء](errors.md).

يُستثنى من ذلك التكرار على الموارد: `404` على صفحة بعد الأولى ينهي التكرار دون رفع خطأ، كما
في 0.1، لأن DRF وواجهات مشابهة تجيب بـ`404` بعد آخر صفحة. راجع
[التكرار الكسول](resources.md).

## 4. توجيه الوسائط يأتي من تعليقات الأنواع

يُحسم التوجيه من تعليقات الأنواع وقت الزخرفة، لا من القيم وقت التشغيل. وسائط `dict` غير
المُعلَّقة تذهب الآن إلى **الجسم**، لا إلى سلسلة الاستعلام. استخدم [العلامات](parameters.md)
للتحكّم الصريح.

=== "0.1"

    ```python
    @get("/search")
    def search(self, response: Response, filters: dict):
        ...                       # `filters` was sent as query parameters
    ```

=== "0.2"

    ```python
    @get("/search")
    def search(self, status: str, limit: int = 10) -> dict:
        raise NotImplementedError   # scalars go to the query: ?status=...&limit=10
    ```

قيمة `dict` **لا** تُفكَّك إلى مفاتيح استعلام: لو عُلِّقت بـ `Query()` لأُرسلت قيمة واحدة نصّية.
ولإرسال عدّة مفاتيح استعلام، صرّح بكل واحد منها وسيطًا قياسيًا مستقلًا (كما أعلاه). ويجب الآن
أن يكون لكل وسيط تعليق نوع.

## 5. أُسقط دعم بايثون 3.9

=== "0.1"

    ```toml
    requires-python = ">=3.9"
    ```

=== "0.2"

    ```toml
    requires-python = ">=3.10"
    ```

يدعم أساس 0.2 بايثون من 3.10 إلى 3.13، ما يتيح لك أيضًا كتابة `str | None` و`list[User]` في
تعليقات الأنواع.

## 6. وسائط مُنشئ العميل بعد `base_url` صارت مفتاحية فقط

=== "0.1"

    ```python
    client = MyClient("https://api.example.com", engine, auth)
    ```

=== "0.2"

    ```python
    client = MyClient("https://api.example.com", engine=engine, auth=auth)
    ```

## 7. `Resource.delete()` تُعيد `None`

صارت الموارد أيضًا عامّة (generic) على نموذجها، وترفع `ResponseValidationError` (لا
`ValidationError` الخام من Pydantic) عندما يفشل التحقق من سجلّ أو صفحة.

=== "0.1"

    ```python
    class Users(AsasResource):
        path = "/users"
        model = User

    response = client.users.delete(1)     # a Response
    ```

=== "0.2"

    ```python
    class Users(AsasResource[User]):
        path = "/users"

    client.users.delete(1)                # None; raises on a non-2xx status
    ```

الكود الذي كان يلتقط `pydantic.ValidationError` حول نداءات الموارد ينبغي أن يلتقط
`asas.ResponseValidationError` (وتحمل خاصيته `.error` الاستثناء الأصلي).

## 8. `APIKeyAuth` في كوكي يستخدم `Request.cookies`

=== "0.1"

    ```python
    # wrote a raw `Cookie: session=...` header
    request.headers["Cookie"]
    ```

=== "0.2"

    ```python
    # writes to the new cookies field, which engines send
    request.cookies["session"]
    ```

## 9. على المحرّكات المخصّصة رفع `TransportError` وإرسال الكوكيز

=== "0.1"

    ```python
    def send(self, request: Request) -> Response:
        resp = self.session.request(request.method, request.url, headers=request.headers)
        return Response(resp.status_code, dict(resp.headers), resp.content, resp.text)
    ```

=== "0.2"

    ```python
    def send(self, request: Request) -> Response:
        try:
            resp = self.session.request(
                request.method,
                request.url,
                headers=request.headers,
                cookies=request.cookies,
                timeout=request.timeout,
            )
        except requests.RequestException as exc:
            raise TransportError(str(exc), request) from exc
        return Response(resp.status_code, dict(resp.headers), resp.content, resp.text)
    ```

راجع [عقد المحرّك](engines.md).

## إصلاحات أصغر تحصل عليها مجانًا

- تُرمَّز قيم المسار ترميزًا نسبيًا (`quote(str(v), safe="")`)، وكذلك معرّفات الموارد في
  `get` / `update` / `delete`.
- تُفرَّغ أجسام الطلب بصيغة آمنة لـ JSON وبحسب الاسم المستعار (`datetime` و`UUID` و`Decimal`
  والتعدادات).
- يطبّق المحرّك الافتراضي إعدادات العميل الافتراضية: `AsasClient(headers=..., timeout=...)`
  صار يُعمَل به. كانت تُهمَل بصمت سابقًا.
- صار `Payload.json` من النوع `Any`.
- العملاء مديرو سياق (context managers) ولديهم `close()` / `aclose()`.
