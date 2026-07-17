# banana

**توليد الصور داخل Claude Code**
*Image generation inside Claude Code*

اكتب فكرة، واحصل على صورة. Claude يشتغل **مديراً إبداعياً**: يفهم قصدك، يختار
العدسة المناسبة، يبني البرومبت الاحترافي، ثم يولّد عبر نماذج Gemini.

```
/banana generate صورة غلاف لمقال عن القهوة المختصة
```

أنت تكتب فكرة. هو يكتب البرومبت.

---

## التثبيت · Install

```bash
git clone https://github.com/hussamalraddadi/banana.git
cd banana
bash install.sh
```

ثم مفتاح من [Google AI Studio](https://aistudio.google.com/apikey):

```bash
echo 'export GOOGLE_AI_API_KEY="مفتاحك"' >> ~/.zshrc && source ~/.zshrc
```

أعد تشغيل Claude Code وجرّب:

```
/banana generate a red cube on a white background
```

> **الفوترة شرط لا خيار.** جوجل لا تتيح توليد الصور على الطبقة المجانية إطلاقاً.
> فعّل الفوترة، وضع سقف صرف من لوحة جوجل.

---

## الأوامر · Commands

| الأمر | ماذا يفعل |
|---|---|
| `/banana generate <فكرة>` | يولّد صورة. Claude يبني البرومبت بنفسه. |
| `/banana edit <مسار> <تعليمات>` | يحرّر صورة موجودة. يحسّن تعليمتك قبل تنفيذها. |
| `/banana chat` | جلسة إبداعية، يغيّر مكوّناً واحداً كل مرة حتى تنضج الفكرة. |
| `/banana batch <فكرة> [عدد]` | تنويعات دفعة واحدة. يقبل ملف CSV. |
| `/banana inspire [نمط]` | أفكار برومبتات حسب المجال. |
| `/banana preset` | يحفظ هوية بصرية ثابتة ويعيد استخدامها. |
| `/banana cost` | يتتبّع الإنفاق ويقدّر أي دفعة قبل تنفيذها. |

---

## تسعة أنماط · Nine domain modes

`Cinema` · `Product` · `Portrait` · `Editorial` · `UI/Web` · `Logo` · `Landscape`
· `Abstract` · `Infographic`

لكل نمط عدسة مختلفة. نمط المنتجات يركّز على الخامات وإضاءة الاستوديو، والسينمائي
على الكاميرا واتجاه الضوء، والشعار على البناء الهندسي وقابلية التصغير. النمط
يحدّد أي التفاصيل تحمل الوزن.

---

## كيف يبني البرومبت · How it writes the prompt

خمسة مكوّنات: **الموضوع ← الفعل ← السياق ← التكوين ← الأسلوب والإضاءة**.

والقاعدة الحاكمة:

> **صف ما تراه الكاميرا، لا ما تعنيه الصورة.**

النموذج لا يرسم المعاني، يرسم الأسطح والضوء والهندسة. لذلك «إعلان قوي عن الحرية»
لا ينتج شيئاً، بينما «شخص وحيد على طريق ساحلي فجراً، ذراعاه مرتخيتان» ينتج صورة.

التفاصيل في [`references/prompt-engineering.md`](skills/banana/references/prompt-engineering.md).

---

## التكلفة · Cost

الدقة هي مقبض التكلفة. الـ4K يكلّف ٣٫٤ أضعاف الـ512 على النموذج نفسه، فجرّب
رخيصاً ثم أنتج الفائز عالياً.

| النموذج | 1K | 2K | 4K |
|---|---|---|---|
| `gemini-3.1-flash-image` (الافتراضي) | $0.067 | **$0.101** | $0.151 |
| `gemini-3-pro-image` | $0.134 | $0.134 | $0.24 |
| `gemini-3.1-flash-lite-image` | $0.0336 | — | — |
| `gemini-2.5-flash-image` | $0.039 | — | — |

خصم Batch: **٥٠٪** على كل النماذج.

الأسعار محقّقة من [صفحة جوجل الرسمية](https://ai.google.dev/gemini-api/docs/pricing)
بتاريخ ١٧ يوليو ٢٠٢٦، وتُحسب من التوكنز لا من السعر المقرّب. حيث تضع جوجل شرطة
هنا فهي لا تنشر الرقم، والأداة تقول `unknown` ولا تخمّن.

```bash
/banana cost estimate --model gemini-3.1-flash-image --resolution 2K --count 20
```

---

## البنية · How it's built

| | |
|---|---|
| **وجهة اتصال واحدة** | `generativelanguage.googleapis.com`. لا شيء غيرها. |
| **ملف واحد يلمس الشبكة** | `gemini_client.py`. تبي تعرف وين يروح مفتاحك؟ اقرأه وحده. |
| **صفر تبعيات** | مكتبة بايثون المعيارية وحدها. |
| **مفتاحك** | من متغيّر البيئة، ويُرسل لجوجل في ترويسة. لا يُكتب في أي ملف إعدادات. |

المثبّت ينسخ ملفات محلياً فقط. لا يحمّل شيئاً ولا يركّب حزماً ولا يلمس إعداداتك.

### الإزالة · Uninstall

```bash
bash install.sh --uninstall
```

تحذف `~/.claude/skills/banana/` فقط. بياناتك في `~/.banana/` تبقى لك.

---

## المتطلبات · Requirements

- Claude Code
- Python 3 · المكتبة المعيارية فقط
- مفتاح Google AI Studio مع فوترة مفعّلة
- ImageMagick · اختياري، للمعالجة اللاحقة فقط

---

## الرخصة · License

MIT — راجع [`LICENSE`](LICENSE).

الفكرة الأساسية، أن يعمل Claude مديراً إبداعياً أمام نماذج الصور، مستوحاة من
[`AgriciDaniel/banana-claude`](https://github.com/AgriciDaniel/banana-claude).
التنفيذ هنا مستقل بالكامل وغير تابع له.

**Hussam Alraddadi**
