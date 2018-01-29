library ieee ;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library mylib2;
use mylib2.mypackage.all;

entity adder_testbench is
end adder_testbench;

architecture beh of adder_testbench is
  signal IN1  : unsigned(7 downto 0);
  signal IN2  : unsigned(7 downto 0);
  signal IN3  : unsigned(7 downto 0);
  signal IN4  : unsigned(7 downto 0);
  signal OUT1 : unsigned(9 downto 0);
begin
  adder0 : adder4
  generic map(DATA_WIDTH=>8)
  port map(A => IN1,
           B => IN2,
           C => IN3,
           D => IN4,
           X => OUT1);

  process
  begin
  IN1 <= x"02";
  IN2 <= x"02";
  IN3 <= x"01";
  IN4 <= x"03";
  wait for 10 ns;
  ASSERT FALSE REPORT "end of test" SEVERITY NOTE;
  wait;
  end process;
end beh;
