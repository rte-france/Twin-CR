// A trigger firing an action on several elements. The body is one action over a list, the same as any other
// statement over a list, so all of its elements are acted on when the condition holds.
when load "01_1" output "P" > 200, decrease load ["03_1", "04_1"] input "P" by 5%;
