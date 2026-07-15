const RU_MAX_DIGITS = 11;
const INTL_MAX_LEN = 20;

/** Маска телефона.
 *
 * Российские номера приводит к «+7 (___) ___-__-__». Номер, начатый с «+» и не
 * с семёрки, считает иностранным и не переформатирует: иначе +372… молча
 * превращался в +7 (372)… и номер терялся.
 */
export function formatPhoneRu(input: string): string {
  if (!input) return "";
  const raw = input.trimStart();

  // «+» без цифр — поле стирают, не навязываем +7 обратно.
  if (raw === "+") return "+";

  if (raw.startsWith("+") && !raw.startsWith("+7")) {
    return "+" + raw.slice(1).replace(/[^\d\s()-]/g, "").slice(0, INTL_MAX_LEN);
  }

  let digits = raw.replace(/\D/g, "");
  if (!digits) return "";
  if (digits.startsWith("8")) digits = "7" + digits.slice(1);
  if (!digits.startsWith("7")) digits = "7" + digits;
  digits = digits.slice(0, RU_MAX_DIGITS);

  const rest = digits.slice(1);
  let out = "+7";
  if (rest.length === 0) return out;
  out += " (" + rest.slice(0, 3);
  if (rest.length < 3) return out;
  out += ")";
  if (rest.length === 3) return out;
  out += " " + rest.slice(3, 6);
  if (rest.length <= 6) return out;
  out += "-" + rest.slice(6, 8);
  if (rest.length <= 8) return out;
  out += "-" + rest.slice(8, 10);
  return out;
}
