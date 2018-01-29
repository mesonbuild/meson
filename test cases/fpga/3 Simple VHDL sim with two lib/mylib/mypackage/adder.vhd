-- Adder DUT
library ieee ;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity adder is
generic(
    DATA_WIDTH : positive := 4);
port(
    A : in  unsigned(DATA_WIDTH-1 downto 0);
    B : in  unsigned(DATA_WIDTH-1 downto 0);
    X : out unsigned(DATA_WIDTH downto 0)
    );
end adder;

architecture RTL of adder is
begin

    process(A, B)   
    begin
	  X <= resize(A, X'length) + B; 
    end process;	

end RTL; 
