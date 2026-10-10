// Numbers of the figures, read from the files their runs write
// (data/results/<name>.json, through record() in tools/figures/make_figures.py),
// so a new run updates a diagram without editing it.
//
//   #import "/lib/data.typ": res, val, num, pct, sci
//   #num(val("render_times", "median_ms"), digits: 3) ms
//
// `val` takes a key, or a path "a.b.2" into nested values and lists;
// a key that itself contains a dot is matched first.

#let res(name) = json("/data/results/" + name + ".json")

#let val(name, key) = {
  let v = res(name).values
  if key in v { return v.at(key) }
  for part in key.split(".") {
    if type(v) == array { v = v.at(int(part)) } else {
      assert(part in v, message: "no value '" + key + "' in results of " + name)
      v = v.at(part)
    }
  }
  v
}

// A number with exactly `digits` decimals, and a true minus sign.
#let fixed(x, digits) = {
  let r = calc.round(float(x), digits: digits)
  let t = str(calc.abs(r))
  let parts = t.split(".")
  let frac = if parts.len() > 1 { parts.at(1) } else { "" }
  let body = if digits == 0 { parts.at(0) } else { parts.at(0) + "." + frac + "0" * (digits - frac.len()) }
  if r < 0 { "−" + body } else { body }
}

// Plain number, fixed decimals.
#let num(x, digits: 2) = fixed(x, digits)

// A fraction shown as a percentage: pct(0.0031) -> 0.31 %.
#let pct(x, digits: 2, sign: false) = {
  let s = fixed(100 * float(x), digits)
  (if sign and float(x) >= 0 { "+" } else { "" }) + s + "\u{00A0}%"
}

// Scientific notation as math: sci(1.3e-8) -> 1.3 × 10^(-8); `abs` drops the sign.
#let sci(x, digits: 1, abs: false) = {
  let y = if abs { calc.abs(float(x)) } else { float(x) }
  if y == 0 { return $0$ }
  let e = int(calc.floor(calc.log(calc.abs(y), base: 10)))
  let m = y / calc.pow(10.0, e)
  if calc.abs(calc.round(m, digits: digits)) >= 10 { m = m / 10; e = e + 1 }
  let ms = fixed(m, digits)
  // between 1 and 1000 the plain number reads better: 13.4, not 1.34 x 10^1
  if e >= 0 and e <= 2 { return $#fixed(y, calc.max(digits - e, 0))$ }
  if e == 0 { $#ms$ } else if ms == "1" or ms == "1." + "0" * digits { $10^(#e)$ } else { $#ms times 10^(#e)$ }
}

// Statistics of a list of values.
#let mean(xs) = xs.map(float).sum() / xs.len()
#let lo(xs) = calc.min(..xs.map(float))
#let hi(xs) = calc.max(..xs.map(float))
#let amax(xs) = calc.max(..xs.map(x => calc.abs(float(x))))
