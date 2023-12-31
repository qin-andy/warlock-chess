import React, { useEffect, useState } from 'react';
import { CellData, GameResult, Player } from '../types';
import Cell from './Cell';

import './Chart.css';

const Chart = (props: {
  games: GameResult[] | undefined;
  players: Player[] | undefined;
  matchups: GameResult[][][] | undefined;
  cellData: CellData[][] | undefined;
  openCell: Function;
  highlightCell: Function;
}) => {
  const { players, games, matchups, cellData, openCell, highlightCell } = props;
  const dimension = players == null ? 3 : players.length

  // consolidate cell data in components. Also builds chart labels
  const createCellComponents = (cellData?: CellData[][]) => {
    if (!cellData || !players) return [];
    let components = []

    // Also need to build labels. First "row" of components is all labels.
    let label_row = [(<div className='label-row-item' key={-1} />)]; // first label row 
    // initialized with one elemnt in it,representing the first diagonal one. this one is empty.
    console.log(cellData)

    // Reverse (not in place) so the labels will be ordered form least to highest elo
    let reverse_players = players.map((player, index) => { return players[players.length - 1 - index] });
    for (let i = 1; i < dimension + 1; i++) {
      let label = (
        <div className='label-row-item' key={'player' + i}>
          {reverse_players[i - 1].name}
        </div>
      );
      label_row.push(label);
    }

    // Create first row into the components grid
    components.push(
      <div className='chart-row' key={'row' + -1}>
        {label_row}
      </div>
    );

    // Start generating the rest of the rows
    for (let y = 0; y < cellData.length; y++) {
      let y_row = [];
      for (let x = 0; x < cellData.length; x++) {
        // first element of every row has to be a label
        if (x === 0) {
          let label = (
            <div className='label-column-item' key={'label col' + x}>
              {reverse_players[y].name}
            </div>
          );
          y_row.push(label);
        }

        let c = cellData[y][x];
        let element = (
          <Cell
            key={c.x + ',' + c.y}
            x={x} // Note we're using the x, y coords from the iteration rather than CELL.X and CELL.Y.
            y={y}
            games={c.games}
            highlighted={c.highlighted}
            open={c.open}
            openCell={openCell}
            highlightCell={highlightCell}
          />
        )
        y_row.push(element);
      }

      components.push(
        <div className='chart-row' key={y}>
          {y_row}
        </div>
      );
    }
    return components;
  }

  return (
    <>
      <div className='chart-container'>
        {createCellComponents(cellData)}
      </div>
    </>
  )
}

export default Chart;