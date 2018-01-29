library ieee ;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

PACKAGE mypackage IS

COMPONENT adder IS
GENERIC(
    DATA_WIDTH : positive := 4);
PORT(
    A : in  unsigned(DATA_WIDTH-1 downto 0);
    B : in  unsigned(DATA_WIDTH-1 downto 0);
    X : out unsigned(DATA_WIDTH downto 0)
    );
END COMPONENT;
END PACKAGE;
