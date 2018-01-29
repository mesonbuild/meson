library ieee ;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

PACKAGE mypackage IS

COMPONENT adder4 IS
generic(
    DATA_WIDTH : positive := 4);
port(
    A : in  unsigned(DATA_WIDTH-1 downto 0);
    B : in  unsigned(DATA_WIDTH-1 downto 0);
    C : in  unsigned(DATA_WIDTH-1 downto 0);
    D : in  unsigned(DATA_WIDTH-1 downto 0);
    X : out unsigned(DATA_WIDTH+1 downto 0)
    );
END COMPONENT;
END PACKAGE;
