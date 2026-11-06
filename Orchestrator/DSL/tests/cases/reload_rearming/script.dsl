// A when_rearming that has already fired once and gone back to armed before the dump. Whether it fires again
// afterwards depends on its rearm state surviving: restored as disarmed it would stay silent for good.
when_rearming load "01_1" output "P" > 150, decrease load "01_1" input "P" by 5%;
