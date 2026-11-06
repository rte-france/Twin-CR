// A list target is one action on several elements, the same as an anonymous cluster, so the statement is a single
// event. That is what makes the queue show one row for it, a deletion cancel the statement the user wrote, and an
// edit work at all: the text handed back re-expands to exactly one event, which is what PUT requires.
after 8 seconds, decrease load ["03_1", "04_1"] input "P" by 5%;
