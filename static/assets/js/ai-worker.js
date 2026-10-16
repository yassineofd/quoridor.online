/* Runs the computer opponent off the main thread so the page stays responsive while it thinks. */
importScripts('engine.js', 'ai.js');

self.onmessage = function (e) {
  var d = e.data, game = self.Quoridor.Game.fromJSON({ moves: d.moves });
  self.postMessage({ id: d.id, move: self.QuoridorAI.chooseMove(game, { level: d.level }) });
};
