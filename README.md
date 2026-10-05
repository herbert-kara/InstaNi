# InstaNi — آپدیت خودکار

موتور پچ InstaNi به صورت یک **GitHub Action** در `ci/ci.yml` نوشته شده. وقتی SamMods نسخه جدید InstaPro را منتشر کرد:

1. دکمه **Actions → Build InstaNi → Run workflow** را بزن (یا فایل `update-trigger.txt` را در main پوَش کن تا خودکار شروع شود).
2. **URL** آخرین فایل اینستاگرام مد (معمولاً `InstaPro vXX By.SamMods.apk`) را وارد کن
   - یا از پیش در **Settings → Secrets and variables → Actions** یک secret به نام `INSTAPRO_URL` تعریف کن.
3. صبر کن؛ پس از چند دقیقه فایل `out/InstaNi-latest.apk` به‌صورت یک **GitHub Release** منتشر می‌شود.

**نکته مهم:** امضا همیشه با کلید تست `AOSP` (یکسان با اصل SamMods) انجام می‌شود تا چک امضای بومی مود پاس شود و لاگ‌اوت ایجاد نکند.
بعد از انتشار، فقط روی آیکون `InstaNi` نصب کن — با همان شماره حفظ می‌شود.

مدیریت تبلیغات سازنده، پاپ‌آپ آپدیت و قفل PIN توسط همین پچ‌ها انجام می‌شود؛ هسته اینستاگرام دست‌نخورده می‌ماند.
