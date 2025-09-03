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
  ctx.fillStyle = '#222';
  ctx.fillRect(0,0,320,200);
  ctx.fillStyle = '#555';
  ctx.fillRect(0,0,320,20);
  ctx.fillRect(0,180,320,20);
  ctx.fillRect(0,0,20,200);
  ctx.fillRect(300,0,20,200);
  ctx.fillStyle = '#888';
  for (let x=140; x<=180; x+=20) {
    ctx.fillRect(x,20,4,160);
  }
}

drawScene();
