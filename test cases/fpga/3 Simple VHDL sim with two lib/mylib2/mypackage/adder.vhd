-- Adder DUT
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library mylib;
use mylib.mypackage.all;

entity adder4 is
generic(
    DATA_WIDTH : positive := 4);
port(
    A : in  unsigned(DATA_WIDTH-1 downto 0);
    B : in  unsigned(DATA_WIDTH-1 downto 0);
    C : in  unsigned(DATA_WIDTH-1 downto 0);
    D : in  unsigned(DATA_WIDTH-1 downto 0);
    X : out unsigned(DATA_WIDTH+1 downto 0)
    );
end adder4;

architecture RTL of adder4 is
SIGNAL adder1_out : std_logic_vector(DATA_WIDTH downto 0);
SIGNAL adder2_out : std_logic_vector(DATA_WIDTH downto 0);

begin

adder1:adder
generic map(DATA_WIDTH)
port map(A,B,adder1_out);

adder2:adder
generic map(DATA_WIDTH)
port map(C,D,adder2_out);

adder3:adder
generic map(DATA_WIDTH+1)
port map(adder1_out,adder1_out,X);

end RTL; 
