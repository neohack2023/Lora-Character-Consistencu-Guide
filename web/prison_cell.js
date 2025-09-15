class Player {
  constructor() {
    this.items = new Set(['Lockpick']);
    this.skills = { lockpicking: 60, speechcraft: 30 };
    this.spells = new Set(['Unlock I']);
    this.magicka = 10;
    this.strength = 80;
    this.reputation = 5;
    this.escapeMethod = null;
  }
  hasItem(item) { return this.items.has(item); }
  knowsSpell(spell) { return this.spells.has(spell); }
}

function attemptLockpick(player, difficulty=50) {
  if (player.hasItem('Lockpick') && (player.skills.lockpicking || 0) >= difficulty) {
    player.escapeMethod = 'Lockpick';
    return true;
  }
  return false;
}

function attemptSpellUnlock(player, cost=5) {
  if (player.knowsSpell('Unlock I') && player.magicka >= cost) {
    player.magicka -= cost;
    player.escapeMethod = 'Spell';
    return true;
  }
  return false;
}

function attemptPersuadeGuard(player, threshold=40) {
  const score = (player.skills.speechcraft || 0) + player.reputation;
  if (score >= threshold) {
    player.escapeMethod = 'Persuade';
    return true;
  }
  return false;
}

function attemptBreakDoor(player, threshold=70) {
  if (player.strength >= threshold) {
    player.escapeMethod = 'Violent';
    return true;
  }
  return false;
}

function attemptTunnelEscape(player, hasTunnel=true) {
  if (hasTunnel) {
    player.escapeMethod = 'Tunnel';
    return true;
  }
  return false;
}

const player = new Player();
const msg = document.getElementById('message');

document.getElementById('lockpick').onclick = () => {
  msg.textContent = attemptLockpick(player)
    ? 'Success! You picked the lock and slip into the hall.'
    : 'The lock refuses to yield.';
  if (player.escapeMethod) endGame();
};

document.getElementById('spell').onclick = () => {
  msg.textContent = attemptSpellUnlock(player)
    ? 'The spell clicks the lock open.'
    : 'Your spell fizzles uselessly.';
  if (player.escapeMethod) endGame();
};

document.getElementById('persuade').onclick = () => {
  msg.textContent = attemptPersuadeGuard(player)
    ? 'The guard takes pity and opens the door.'
    : 'The guard ignores your pleas.';
  if (player.escapeMethod) endGame();
};

document.getElementById('break').onclick = () => {
  msg.textContent = attemptBreakDoor(player)
    ? 'With a mighty blow you break the door.'
    : 'You slam against the door, but it holds firm.';
  if (player.escapeMethod) endGame();
};

document.getElementById('tunnel').onclick = () => {
  msg.textContent = attemptTunnelEscape(player)
    ? 'Behind a loose stone you discover a crawlspace to freedom.'
    : 'You find no sign of a tunnel.';
  if (player.escapeMethod) endGame();
};

function endGame() {
  document.querySelectorAll('#ui button').forEach(b => b.disabled = true);
}

function drawScene() {
  const ctx = document.getElementById('game').getContext('2d');

  // base clear
  ctx.fillStyle = '#222';
  ctx.fillRect(0,0,320,200);

  // floor
  ctx.fillStyle = '#333';
  ctx.beginPath();
  ctx.moveTo(20,180);
  ctx.lineTo(300,180);
  ctx.lineTo(260,120);
  ctx.lineTo(60,120);
  ctx.closePath();
  ctx.fill();

  // ceiling
  ctx.fillStyle = '#444';
  ctx.beginPath();
  ctx.moveTo(20,20);
  ctx.lineTo(300,20);
  ctx.lineTo(260,120);
  ctx.lineTo(60,120);
  ctx.closePath();
  ctx.fill();

  // left wall
  ctx.fillStyle = '#555';
  ctx.beginPath();
  ctx.moveTo(20,20);
  ctx.lineTo(60,120);
  ctx.lineTo(60,180);
  ctx.lineTo(20,180);
  ctx.closePath();
  ctx.fill();

  // right wall
  ctx.beginPath();
  ctx.moveTo(300,20);
  ctx.lineTo(260,120);
  ctx.lineTo(260,180);
  ctx.lineTo(300,180);
  ctx.closePath();
  ctx.fill();

  // back wall
  ctx.fillStyle = '#666';
  ctx.beginPath();
  ctx.moveTo(60,120);
  ctx.lineTo(260,120);
  ctx.lineTo(260,180);
  ctx.lineTo(60,180);
  ctx.closePath();
  ctx.fill();

  // door bars
  ctx.fillStyle = '#888';
  for (let x = 120; x <= 200; x += 20) {
    ctx.fillRect(x - 2, 20, 4, 160);
  }

  // bunk on the left
  ctx.fillStyle = '#777';
  ctx.beginPath();
  ctx.moveTo(60,150);   // front-left
  ctx.lineTo(130,150);  // front-right
  ctx.lineTo(120,160);  // back-right
  ctx.lineTo(50,160);   // back-left
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#666';
  ctx.fillRect(50,160,70,10);

  // simple table on the right
  ctx.fillStyle = '#a6753a';
  ctx.beginPath();
  ctx.moveTo(190,150);
  ctx.lineTo(250,150);
  ctx.lineTo(240,160);
  ctx.lineTo(180,160);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#8b5a2b';
  ctx.fillRect(180,160,60,10);
}

drawScene();
