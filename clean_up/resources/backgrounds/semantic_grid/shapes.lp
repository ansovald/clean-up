% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 0. Shape catalogue (finite set) 
% shape(SID,BX,BY): 
%   assign each ShapeID a set of offsets (BX,BY) relative to starting cell.
%   BX and BY measures the number of offset blocks **before scaling by span**
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% In comment, Shape B-Idx: B is the number of blocks, Idx is index

% Shape 2-1: 2 blocks, vertical
% ```
% B
% B
% ```
shape(1,0,0).
shape(1,0,1).

% Shape 2-2: 2 blocks, horizontal
% `BB`
shape(2,0,0).
shape(2,1,0).

% Shape 3-1: 3 blocks stacked vertically
% ```
% B
% B
% B
% ```
shape(3,0,0).  
shape(3,0,1).
shape(3,0,2).


% % Shape 3-3: 3 blocks in a 2x2 grid of blocks
% % ```
% % BB
% % B
% % ```
% shape(4,0,0).
% shape(4,0,1).
% shape(4,1,0).

% Shape 3-4
% ```
% B
% BB
% ```
shape(4,0,0).
shape(4,0,1).
shape(4,1,1).

% % Shape 3-5
% % ```
% %  B
% % BB
% % ```
% shape(8,0,1).
% shape(8,1,1).
% shape(8,1,0).

% % Shape 3-6
% % ```
% % BB
% %  B
% % ```
% shape(9,0,0).
% shape(9,1,0).
% shape(9,1,1).

% Shape 4-1
% ```
% B
% B
% B
% B
% ```
shape(5,0,0).  
shape(5,0,1).
shape(5,0,2).
shape(5,0,3).

% Shape 4-2
% ```
% BB
% BB
% ```
shape(6,0,0).  
shape(6,0,1).
shape(6,1,0).
shape(6,1,1).


% Shape 5-1
% ```
% B
% B
% B
% B
% B
% ```
shape(7,0,0).  
shape(7,0,1).
shape(7,0,2).
shape(7,0,3).
shape(7,0,4).

% Shape 5-2
% ```
% BB
% B
% B
% B
% ```

% Shape 5-3
% ```
% BB
% BB
%  B
% ```
shape(8,0,0).  
shape(8,0,1).
shape(8,1,0).
shape(8,1,1).
shape(8,1,2).

% Shape 6-1
% ```
% B
% B
% B
% B
% B
% B
% ```
% shape(9,0,0).  
% shape(9,0,1).
% shape(9,0,2).
% shape(9,0,3).
% shape(9,0,4).
% shape(9,0,5).

% Shape 6-2
% ```
% BB
% BB
% BB
% ```
shape(9,0,0).  
shape(9,0,1).
shape(9,0,2).
shape(9,1,0).
shape(9,1,1).
shape(9,1,2).