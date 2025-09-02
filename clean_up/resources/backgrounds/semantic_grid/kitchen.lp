% Generate a grid-based layout of kitchen objects, 
% where each object is represented by blocks of cells that form a specific shape, see `shapes.lp`. 
% 
% Usage: 
% (A) Run this script and `shapes.lp` with clingo, set the parameters below,
%        - `width`, `height`: dimensions of the grid
%        - `jitter`: real occupied cell ratio = occupied_ratio +/- jitter
%     And add the below set of atoms: 
         % occupied_ratio(35).  % percentage of occupied cells (0-100)
         % h_padding(2).        % horizontal padding on left and right(0-2 columns on each side)
         % v_padding(1).        % vertical padding on top and bottom (0-1 rows on each edge)

         % left_gutter(true).    % left gutter of each placement (true/false)
         % right_gutter(true).   % right gutter of each placement (true/false)
         % lr_proportional_gutter(true).    % if true, left/right gutter width is proportional to the object width; otherwise fixed to 1
         % bottom_gutter(true).  $ bottom gutter of each placement (true/false)
%     sample command: `clingo kitchen.lp shapes.lp -n 50 -c width=52 -c height=10 -c jitter=2`
% (B) Call clingo through Python API, the constants and atoms are set/added in `generate.py`.
%     command: `python generate.py`. 

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 1. Grid and cell
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
grid_width(width).
grid_height(height).

cell(X,Y) :- X=1..W, Y=1..H, grid_width(W), grid_height(H).

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 2. Object catelogue: object(Span) 
%      - Span: the number of cells a block of object covers horizontally,  
%              that is, the horizontal scaling factor of a block of object; 
%              since Span is unique, it also serves as ObjectID (OID)
%    Each object, when materialized, has a shape, which captures how blocks 
%    of the objects are stacked together, see `shapes.lp`. 
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
object(5).
object(6).
object(7).
object(8).
object(9).

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 3. every combination of shape/3 and object/1 forms all possible placement. 
%    placement_type(PID,SID,OID): 
%      - PID: ID of the placement type
%      - SID: ID of shape  
%      - OID: ID of the object
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
placement_type(PID,SID,OID) :- shape(SID,_,_),
                              object(OID),
                              PID=SID*10+OID.

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 4. from possible placement_type to actual placement realization
%    placement(X,Y,PID,PPID): 
%      - X,Y: coordinates of the top-leftmost cell of the placement
%      - PID: ID of placement_type, it's unique for every SID-OID combination
%      - PPID: ID of the placement, it's unique for every X-Y-SID-OID combination
%    for each placement_type and each cell at X,Y, 
%    if the whole placement respects the boundary of the grid and the padding rows/cols, 
%    then this placement may or may not be added to the answer set 
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% placement(X,Y,PID,PPID): starting at cell(X,Y), an instance of placement_type with PID is realized
%                          and this realization of placement has an unique PPID
{ placement(X,Y,PID,PPID) } :-  placement_type(PID,SID,OID),
                                 object(OID),
                                 MaxBX = #max { BXX : shape(SID,BXX,_) },
                                 MaxBY = #max { BYY : shape(SID,_,BYY) },
                                 grid_width(W), grid_height(H),  
                                 h_padding(HP), v_padding(VP), 
                                 1+HP <= W+1-(MaxBX+1)*OID-HP, X=(1+HP)..(W+1-(MaxBX+1)*OID-HP), 
                                 1+VP <= H-MaxBY-VP, Y=(1+VP)..(H-MaxBY-VP), 
                                 PPID=PID*100000+X*100+Y.

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 5. from actual placement to actual coverage in each cell
%    cover(X,Y,OID,PPID): 
%      - X,Y: the cell at X,Y is occupied 
%      - OID: ID of the object that occupies this cell
%      - PPID: ID of the placement that occupies this cell
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
cover(XX,YY,OID,PPID) :- placement(X,Y,PID,PPID), 
                        placement_type(PID,SID,OID),
                        shape(SID,BX,BY),
                        object(OID), 
                        XX=X..X+(BX+1)*OID-1, 
                        YY=Y+BY.

% if a cell is not covered, then it's empty, 
% adding empty_cell/2 here and assume certain empty_cell(X,Y) in `generate.py` 
% to perturb the order of models showing up
empty_cell(X,Y) :- cell(X,Y), not cover(X,Y,_,_).                         

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 6. elimination based on placement/4 and cover/4
%    with some artificial rules 
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% a cell can only hold at most 1 realization of placement/4 (PPID)
:- cell(X,Y), #count { PPID : cover(X,Y,_,PPID) } > 1.

% every object OID must appear at least 1 time
:- object(OID), not 1 { placement(_,_,PID,PPID) : placement_type(PID,_,OID) }.

% the same shape-object combination cannot appear more than 1 time 
:- placement_type(PID,_,_), 2 { placement(_,_,PID,_) }. 

% every placement should have a horizontal gutter on the left, with fixed width 1
:- left_gutter(true), not lr_proportional_gutter(true),
   placement(X,Y,PID,_),
   placement_type(PID,SID,OID), 
   MaxBY = #max { BYY : shape(SID,_,BYY) },
   XL = X-1, 1 <= XL,   
   YL = Y..Y+MaxBY, 
   cover(XL,YL,_,_). 

% every placement should have a horizontal gutter on the right, with fixed width 1
:- right_gutter(true), not lr_proportional_gutter(true),
   placement(X,Y,PID,_),
   placement_type(PID,SID,OID), 
   MaxBX = #max { BXX : shape(SID,BXX,_) },
   MaxBY = #max { BYY : shape(SID,_,BYY) },
   grid_width(W),
   XR = X+(MaxBX+1)*OID,   
   YR = Y..Y+MaxBY, 
   cover(XR,YR,_,_). 

% every placement should have a horizontal gutter on the left, with proportional width
:- left_gutter(true), lr_proportional_gutter(true),
   placement(X,Y,PID,_),
   placement_type(PID,SID,OID), 
   MaxBY = #max { BYY : shape(SID,_,BYY) },
   XL = X-OID/3..X-1, 1 <= XL,
   YL = Y..Y+MaxBY, 
   cover(XL,YL,_,_). 

% every placement should have a horizontal gutter on the right, with proportional width
:- right_gutter(true), lr_proportional_gutter(true),
   placement(X,Y,PID,_),
   placement_type(PID,SID,OID), 
   MaxBX = #max { BXX : shape(SID,BXX,_) },
   MaxBY = #max { BYY : shape(SID,_,BYY) },
   grid_width(W),
   XR = X+(MaxBX+1)*OID..X+(MaxBX+1)*OID+OID/3-1,
   YR = Y..Y+MaxBY, 
   cover(XR,YR,_,_).    
   

% every placement should have a gutter of heigh 1 on the bottom
:- bottom_gutter(true), 
   placement(X,Y,PID,_),
   placement_type(PID,SID,OID), 
   MaxBX = #max { BXX : shape(SID,BXX,_) },
   MaxBY = #max { BYY : shape(SID,_,BYY) },
   grid_width(W),
   XB = X..X+(MaxBX+1)*OID-1,
   YB = Y+MaxBY+1,   
   cover(XB,YB,_,_).
   
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 7. Occupied cells and empty cell ratio constraint
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
covered_cells(N) :- N = #count { X,Y : cover(X,Y,OID,PPID) }.
total_cells(W*H) :- grid_width(W), grid_height(H).

% Avoid fractional arithmetic
% C / T ∈ [R-J, R+J]
:- total_cells(T), covered_cells(C), occupied_ratio(R), C*100 / T < R - jitter.
:- total_cells(T), covered_cells(C), occupied_ratio(R), C*100 / T > R + jitter.


% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 8. Output
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#show placement/4.
#show cover/4.
