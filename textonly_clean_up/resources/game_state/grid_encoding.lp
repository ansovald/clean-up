% Define possible grid objects
% numbers: connectivity to the left, right, upwards, downwards
frame("│",0,0,1,1).
frame("─",1,1,0,0).
frame("┌",0,1,0,1).
frame("┐",1,0,0,1).
frame("└",0,1,1,0).
frame("┘",1,0,1,0).
frame("┼",1,1,1,1).
frame("├",0,1,1,1).
frame("┤",1,0,1,1).
frame("┬",1,1,0,1).
frame("┴",1,1,1,0).
frame("◌",-1,-1,-1,-1).

corner("┌";"┐";"└";"┘").
branch("├";"┤";"┬";"┴";"┼").

1 { cell(X,Y,F) : frame(F,_,_,_,_) } 1 :- X=0..W, Y=0..H, grid_size(W,H).

% make sure there are no empty connectors to the side
:- cell(0,Y,F), frame(F,1,_,_,_).
:- cell(W,Y,F), grid_size(W,_), frame(F,_,1,_,_).
:- cell(X,0,F), frame(F,_,_,1,_).
:- cell(X,H,F), grid_size(_,H), frame(F,_,_,_,1).
:- cell(0,Y,"◌").
:- cell(W,Y,"◌"), grid_size(W,_).
:- cell(X,0,"◌").
:- cell(X,H,"◌"), grid_size(_,H).

% make sure all frame tiles connect properly
:- cell(X,Y,F1), cell(X-1,Y,F2), frame(F1,1,_,_,_), not frame(F2,_,1,_,_).
:- cell(X,Y,F1), cell(X+1,Y,F2), frame(F1,_,1,_,_), not frame(F2,1,_,_,_).
:- cell(X,Y,F1), cell(X,Y-1,F2), frame(F1,_,_,1,_), not frame(F2,_,_,_,1).
:- cell(X,Y,F1), cell(X,Y+1,F2), frame(F1,_,_,_,1), not frame(F2,_,_,1,_).


% if a tile does not connect to one side, the cell to that side must be empty
:- cell(X,Y,F), frame(F,0,_,_,_), X > 0, not cell(X-1, Y, "◌").
:- cell(X,Y,F), frame(F,_,0,_,_), X < W, grid_size(W,_), not cell(X+1, Y, "◌").
:- cell(X,Y,F), frame(F,_,_,0,_), Y > 0, not cell(X, Y-1, "◌").
:- cell(X,Y,F), frame(F,_,_,_,0), Y < H, grid_size(_,H), not cell(X, Y+1, "◌").

% for corner shapes: if tile connects leftwards and upwards, the upper left cell must be empty, etc.
:- cell(X,Y,F), frame(F,1,_,1,_), not cell(X-1, Y-1, "◌").
:- cell(X,Y,F), frame(F,1,_,_,1), not cell(X-1, Y+1, "◌").
:- cell(X,Y,F), frame(F,_,1,1,_), not cell(X+1, Y-1, "◌").
:- cell(X,Y,F), frame(F,_,1,_,1), not cell(X+1, Y+1, "◌").

% two neighbouring tiles should not both be corners
:- cell(X,Y,F), cell(X+1,Y,F1), corner(F), corner(F1).
:- cell(X,Y,F), cell(X,Y+1,F1), corner(F), corner(F1).

#show cell/3.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% The following lines influence the shape of the resulting grid. %
% All this is taken care of in `generate_grid.py`, but for       %
%         development and testing, it is easier to have it here. %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% grid_size(21,9).

% a slot must have at least 1 neighbouring slot, and 5 at maximum
% :- cell(X,Y,F), grid_size(W,H), 0 < X < W, 0 < Y < H, not 1 <= #count { XA,YA : cell(XA, YA, "◌"), XA=X-1..X+1, YA=Y-1..Y+1 } < 5.

% set the number of single slot compartments
% single(X,Y) :- cell(X,Y,F), grid_size(W,H), 0 < X < W, 0 < Y < H, 1 = #count { XA,YA : cell(XA, YA, "◌"), XA=X-1..X+1, YA=Y-1..Y+1 }.
% :- not 3 = #count { X,Y : single(X,Y) }.

% Limit the number of possible corners and branches, respectively
% :- 12 < #count { X,Y,F : cell(X,Y,F), corner(F) }.
% :- 14 < #count { X,Y,F : cell(X,Y,F), branch(F) }.

% limit number of corners+branches in each row and column
% :- Y=0..H, grid_size(_,H), CC = #count { X,F : cell(X,Y,F), corner(F) }, BC = #count { X,F : cell(X,Y,F), branch(F) }, not CC+BC < 8.
% :- X=0..W, grid_size(W,_), CC = #count { Y,F : cell(X,Y,F), corner(F) }, BC = #count { Y,F : cell(X,Y,F), branch(F) }, not CC+BC < 4.
