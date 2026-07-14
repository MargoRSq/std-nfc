export function formatPhoneRu(input: string): string {
  if (!input) return "";
  let digits = input.replace(/\D/g, "");
  if (digits.startsWith("8")) digits = "7" + digits.slice(1);
  if (!digits.startsWith("7")) digits = "7" + digits;
  digits = digits.slice(0, 11);
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
