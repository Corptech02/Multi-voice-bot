// Advanced Graphics and Animation System for Retro Platformer

class AdvancedGraphics {
    constructor() {
        this.animations = {};
        this.particles = [];
        this.screenShake = { x: 0, y: 0, duration: 0, intensity: 0 };
        this.lightingEffects = [];
        this.time = 0;
    }

    update(deltaTime) {
        this.time += deltaTime;
        
        // Update screen shake
        if (this.screenShake.duration > 0) {
            this.screenShake.duration -= deltaTime;
            this.screenShake.x = (Math.random() - 0.5) * this.screenShake.intensity;
            this.screenShake.y = (Math.random() - 0.5) * this.screenShake.intensity;
        } else {
            this.screenShake.x = 0;
            this.screenShake.y = 0;
        }
        
        // Update particles
        this.particles = this.particles.filter(p => {
            p.life -= deltaTime;
            p.x += p.vx * deltaTime;
            p.y += p.vy * deltaTime;
            p.vy += p.gravity * deltaTime;
            p.opacity = Math.max(0, p.life / p.maxLife);
            p.size *= p.decay;
            return p.life > 0;
        });
        
        // Update lighting effects
        this.lightingEffects = this.lightingEffects.filter(l => {
            l.life -= deltaTime;
            l.radius += l.growth * deltaTime;
            l.opacity = Math.max(0, l.life / l.maxLife);
            return l.life > 0;
        });
    }

    addScreenShake(intensity, duration) {
        this.screenShake.intensity = intensity;
        this.screenShake.duration = duration;
    }

    addMuzzleFlash(x, y, direction) {
        // Add lighting effect
        this.lightingEffects.push({
            x, y,
            radius: 20,
            growth: 100,
            color: 'rgba(255, 255, 100, 0.8)',
            life: 0.1,
            maxLife: 0.1,
            opacity: 1
        });
        
        // Add muzzle particles
        for (let i = 0; i < 5; i++) {
            const angle = direction + (Math.random() - 0.5) * 0.5;
            const speed = 200 + Math.random() * 100;
            this.particles.push({
                x, y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                size: 3 + Math.random() * 2,
                color: `hsl(${30 + Math.random() * 30}, 100%, 70%)`,
                life: 0.2,
                maxLife: 0.2,
                gravity: 0,
                decay: 0.95,
                opacity: 1
            });
        }
    }

    addDoubleJumpEffect(x, y) {
        // Ring effect
        this.lightingEffects.push({
            x, y: y + 20,
            radius: 10,
            growth: 150,
            color: 'rgba(100, 200, 255, 0.5)',
            life: 0.3,
            maxLife: 0.3,
            opacity: 1
        });
        
        // Sparkle particles
        for (let i = 0; i < 12; i++) {
            const angle = (Math.PI * 2 * i) / 12;
            this.particles.push({
                x, y: y + 20,
                vx: Math.cos(angle) * 100,
                vy: Math.sin(angle) * 100 - 50,
                size: 4,
                color: `hsl(${200 + Math.random() * 40}, 100%, 70%)`,
                life: 0.5,
                maxLife: 0.5,
                gravity: 200,
                decay: 0.98,
                opacity: 1
            });
        }
    }

    drawParticles(ctx) {
        ctx.save();
        this.particles.forEach(p => {
            ctx.globalAlpha = p.opacity;
            ctx.fillStyle = p.color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.restore();
    }

    drawLightingEffects(ctx) {
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        this.lightingEffects.forEach(l => {
            const gradient = ctx.createRadialGradient(l.x, l.y, 0, l.x, l.y, l.radius);
            gradient.addColorStop(0, l.color.replace('0.8', `${l.opacity}`));
            gradient.addColorStop(1, 'transparent');
            ctx.fillStyle = gradient;
            ctx.fillRect(l.x - l.radius, l.y - l.radius, l.radius * 2, l.radius * 2);
        });
        ctx.restore();
    }
}

// Advanced Enemy Sprites and Animations
class AdvancedEnemyRenderer {
    drawGoblin(ctx, x, y, frame, facingLeft) {
        const wobble = Math.sin(frame * 0.1) * 2;
        
        // Shadow
        ctx.fillStyle = 'rgba(0,0,0,0.3)';
        ctx.beginPath();
        ctx.ellipse(x, y + 30, 15, 5, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Body
        ctx.fillStyle = '#2d5016';
        ctx.fillRect(x - 12, y - 20 + wobble, 24, 25);
        
        // Belly
        ctx.fillStyle = '#4a7c2e';
        ctx.fillRect(x - 8, y - 10 + wobble, 16, 15);
        
        // Arms with animation
        const armSwing = Math.sin(frame * 0.15) * 10;
        ctx.fillStyle = '#2d5016';
        ctx.save();
        ctx.translate(x - 10, y - 15 + wobble);
        ctx.rotate(armSwing * 0.02);
        ctx.fillRect(-3, 0, 6, 12);
        ctx.restore();
        
        ctx.save();
        ctx.translate(x + 10, y - 15 + wobble);
        ctx.rotate(-armSwing * 0.02);
        ctx.fillRect(-3, 0, 6, 12);
        ctx.restore();
        
        // Legs with walking animation
        const legPhase = Math.sin(frame * 0.2) * 5;
        ctx.fillStyle = '#1f3b0f';
        ctx.fillRect(x - 8 + legPhase, y + 5, 7, 10);
        ctx.fillRect(x + 1 - legPhase, y + 5, 7, 10);
        
        // Head
        ctx.fillStyle = '#2d5016';
        ctx.beginPath();
        ctx.arc(x, y - 25 + wobble, 15, 0, Math.PI * 2);
        ctx.fill();
        
        // Ears
        ctx.fillStyle = '#2d5016';
        ctx.beginPath();
        ctx.moveTo(x - 15, y - 30 + wobble);
        ctx.lineTo(x - 20, y - 40 + wobble);
        ctx.lineTo(x - 10, y - 35 + wobble);
        ctx.fill();
        
        ctx.beginPath();
        ctx.moveTo(x + 15, y - 30 + wobble);
        ctx.lineTo(x + 20, y - 40 + wobble);
        ctx.lineTo(x + 10, y - 35 + wobble);
        ctx.fill();
        
        // Eyes
        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.arc(x - 6, y - 28 + wobble, 3, 0, Math.PI * 2);
        ctx.arc(x + 6, y - 28 + wobble, 3, 0, Math.PI * 2);
        ctx.fill();
        
        // Weapon
        ctx.strokeStyle = '#8B4513';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(x + 12 * (facingLeft ? -1 : 1), y - 10 + wobble);
        ctx.lineTo(x + 25 * (facingLeft ? -1 : 1), y - 30 + wobble);
        ctx.stroke();
        
        // Blade
        ctx.fillStyle = '#C0C0C0';
        ctx.beginPath();
        ctx.moveTo(x + 25 * (facingLeft ? -1 : 1), y - 30 + wobble);
        ctx.lineTo(x + 30 * (facingLeft ? -1 : 1), y - 40 + wobble);
        ctx.lineTo(x + 28 * (facingLeft ? -1 : 1), y - 25 + wobble);
        ctx.fill();
    }

    drawWolf(ctx, x, y, frame, facingLeft) {
        const run = Math.abs(Math.sin(frame * 0.3)) * 5;
        
        // Shadow
        ctx.fillStyle = 'rgba(0,0,0,0.3)';
        ctx.beginPath();
        ctx.ellipse(x, y + 30, 20, 6, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Body
        ctx.fillStyle = '#4a4a4a';
        ctx.beginPath();
        ctx.ellipse(x, y - 5 + run, 25, 15, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Fur detail
        ctx.strokeStyle = '#666';
        ctx.lineWidth = 1;
        for (let i = 0; i < 5; i++) {
            ctx.beginPath();
            ctx.moveTo(x - 20 + i * 10, y - 10 + run);
            ctx.lineTo(x - 18 + i * 10, y - 15 + run);
            ctx.stroke();
        }
        
        // Legs with running animation
        const legCycle = frame * 0.4;
        ctx.fillStyle = '#3a3a3a';
        
        // Front legs
        ctx.save();
        ctx.translate(x - 15, y + 5);
        ctx.rotate(Math.sin(legCycle) * 0.3);
        ctx.fillRect(-3, 0, 6, 15);
        ctx.restore();
        
        ctx.save();
        ctx.translate(x - 8, y + 5);
        ctx.rotate(Math.sin(legCycle + Math.PI) * 0.3);
        ctx.fillRect(-3, 0, 6, 15);
        ctx.restore();
        
        // Back legs
        ctx.save();
        ctx.translate(x + 8, y + 5);
        ctx.rotate(Math.sin(legCycle + Math.PI/2) * 0.3);
        ctx.fillRect(-3, 0, 6, 15);
        ctx.restore();
        
        ctx.save();
        ctx.translate(x + 15, y + 5);
        ctx.rotate(Math.sin(legCycle - Math.PI/2) * 0.3);
        ctx.fillRect(-3, 0, 6, 15);
        ctx.restore();
        
        // Head
        ctx.fillStyle = '#4a4a4a';
        ctx.save();
        ctx.translate(x + (facingLeft ? 20 : -20), y - 10 + run);
        ctx.scale(facingLeft ? -1 : 1, 1);
        
        // Snout
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(-15, -5);
        ctx.lineTo(-15, 5);
        ctx.closePath();
        ctx.fill();
        
        // Main head
        ctx.beginPath();
        ctx.arc(0, 0, 10, 0, Math.PI * 2);
        ctx.fill();
        
        // Ears
        ctx.beginPath();
        ctx.moveTo(-5, -8);
        ctx.lineTo(-8, -15);
        ctx.lineTo(-2, -12);
        ctx.fill();
        
        ctx.beginPath();
        ctx.moveTo(5, -8);
        ctx.lineTo(8, -15);
        ctx.lineTo(2, -12);
        ctx.fill();
        
        ctx.restore();
        
        // Eyes
        ctx.fillStyle = '#ffff00';
        ctx.beginPath();
        ctx.arc(x + (facingLeft ? 15 : -25), y - 12 + run, 2, 0, Math.PI * 2);
        ctx.arc(x + (facingLeft ? 25 : -15), y - 12 + run, 2, 0, Math.PI * 2);
        ctx.fill();
        
        // Tail
        ctx.strokeStyle = '#4a4a4a';
        ctx.lineWidth = 8;
        ctx.beginPath();
        ctx.moveTo(x + (facingLeft ? -25 : 25), y - 5 + run);
        ctx.quadraticCurveTo(
            x + (facingLeft ? -40 : 40), 
            y - 20 + run + Math.sin(frame * 0.2) * 5,
            x + (facingLeft ? -35 : 35), 
            y - 30 + run
        );
        ctx.stroke();
    }

    drawKnight(ctx, x, y, frame, facingLeft) {
        const march = Math.abs(Math.sin(frame * 0.1)) * 2;
        
        // Shadow
        ctx.fillStyle = 'rgba(0,0,0,0.3)';
        ctx.beginPath();
        ctx.ellipse(x, y + 30, 18, 6, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Armor body
        ctx.fillStyle = '#8B8B8B';
        ctx.fillRect(x - 15, y - 20 + march, 30, 30);
        
        // Armor plates
        ctx.strokeStyle = '#5a5a5a';
        ctx.lineWidth = 2;
        ctx.strokeRect(x - 15, y - 20 + march, 30, 10);
        ctx.strokeRect(x - 15, y - 10 + march, 30, 10);
        ctx.strokeRect(x - 15, y + march, 30, 10);
        
        // Arms
        const armSwing = Math.sin(frame * 0.1) * 15;
        ctx.fillStyle = '#8B8B8B';
        
        // Shield arm
        ctx.save();
        ctx.translate(x - 12, y - 15 + march);
        ctx.rotate(-0.3);
        ctx.fillRect(-4, 0, 8, 20);
        ctx.restore();
        
        // Sword arm
        ctx.save();
        ctx.translate(x + 12, y - 15 + march);
        ctx.rotate(0.3 + armSwing * 0.01);
        ctx.fillRect(-4, 0, 8, 20);
        ctx.restore();
        
        // Legs with walking animation
        const legPhase = frame * 0.15;
        ctx.fillStyle = '#6a6a6a';
        
        ctx.save();
        ctx.translate(x - 8, y + 10);
        ctx.rotate(Math.sin(legPhase) * 0.2);
        ctx.fillRect(-4, 0, 8, 15);
        ctx.restore();
        
        ctx.save();
        ctx.translate(x + 8, y + 10);
        ctx.rotate(Math.sin(legPhase + Math.PI) * 0.2);
        ctx.fillRect(-4, 0, 8, 15);
        ctx.restore();
        
        // Helmet
        ctx.fillStyle = '#9a9a9a';
        ctx.fillRect(x - 12, y - 35 + march, 24, 20);
        
        // Helmet visor
        ctx.fillStyle = '#000';
        ctx.fillRect(x - 8, y - 28 + march, 16, 3);
        
        // Helmet plume
        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.moveTo(x, y - 35 + march);
        ctx.quadraticCurveTo(x - 5, y - 45 + march, x, y - 50 + march);
        ctx.quadraticCurveTo(x + 5, y - 45 + march, x, y - 35 + march);
        ctx.fill();
        
        // Shield
        ctx.fillStyle = '#4169E1';
        ctx.save();
        ctx.translate(x - 20 * (facingLeft ? -1 : 1), y - 5 + march);
        ctx.beginPath();
        ctx.moveTo(0, -10);
        ctx.lineTo(-10, -5);
        ctx.lineTo(-10, 10);
        ctx.lineTo(0, 15);
        ctx.lineTo(10, 10);
        ctx.lineTo(10, -5);
        ctx.closePath();
        ctx.fill();
        
        // Shield emblem
        ctx.fillStyle = '#FFD700';
        ctx.beginPath();
        ctx.moveTo(0, -5);
        ctx.lineTo(-5, 0);
        ctx.lineTo(0, 5);
        ctx.lineTo(5, 0);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
        
        // Sword
        ctx.strokeStyle = '#C0C0C0';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(x + 20 * (facingLeft ? -1 : 1), y - 5 + march);
        ctx.lineTo(x + 35 * (facingLeft ? -1 : 1), y - 35 + march + armSwing);
        ctx.stroke();
        
        // Sword guard
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 6;
        ctx.beginPath();
        ctx.moveTo(x + 15 * (facingLeft ? -1 : 1), y - 10 + march);
        ctx.lineTo(x + 25 * (facingLeft ? -1 : 1), y - 10 + march);
        ctx.stroke();
    }

    drawWizard(ctx, x, y, frame, facingLeft) {
        const float = Math.sin(frame * 0.05) * 3;
        const robeFlow = Math.sin(frame * 0.1) * 2;
        
        // Shadow
        ctx.fillStyle = 'rgba(0,0,0,0.2)';
        ctx.beginPath();
        ctx.ellipse(x, y + 30, 20, 6, 0, 0, Math.PI * 2);
        ctx.fill();
        
        // Magical aura
        ctx.save();
        ctx.globalAlpha = 0.3;
        ctx.fillStyle = '#8A2BE2';
        ctx.beginPath();
        ctx.arc(x, y - 10 + float, 35, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
        
        // Robe
        ctx.fillStyle = '#4B0082';
        ctx.beginPath();
        ctx.moveTo(x - 20, y + 20 + float);
        ctx.lineTo(x - 15 + robeFlow, y - 10 + float);
        ctx.lineTo(x - 10, y - 20 + float);
        ctx.lineTo(x + 10, y - 20 + float);
        ctx.lineTo(x + 15 - robeFlow, y - 10 + float);
        ctx.lineTo(x + 20, y + 20 + float);
        ctx.lineTo(x + 15, y + 25 + float);
        ctx.lineTo(x + 10 + robeFlow, y + 20 + float);
        ctx.lineTo(x, y + 15 + float);
        ctx.lineTo(x - 10 - robeFlow, y + 20 + float);
        ctx.lineTo(x - 15, y + 25 + float);
        ctx.closePath();
        ctx.fill();
        
        // Robe trim
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Stars on robe
        ctx.fillStyle = '#FFD700';
        for (let i = 0; i < 3; i++) {
            const starX = x - 10 + i * 10;
            const starY = y + i * 5 + float;
            ctx.save();
            ctx.translate(starX, starY);
            ctx.scale(0.5, 0.5);
            this.drawStar(ctx, 0, 0, 5, 3, 2);
            ctx.restore();
        }
        
        // Arms
        ctx.fillStyle = '#4B0082';
        const armAngle = Math.sin(frame * 0.08) * 0.2;
        
        // Staff arm
        ctx.save();
        ctx.translate(x + 10, y - 15 + float);
        ctx.rotate(0.3 + armAngle);
        ctx.fillRect(-3, 0, 6, 15);
        
        // Hand
        ctx.fillStyle = '#FFE4C4';
        ctx.beginPath();
        ctx.arc(0, 15, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
        
        // Casting arm
        ctx.fillStyle = '#4B0082';
        ctx.save();
        ctx.translate(x - 10, y - 15 + float);
        ctx.rotate(-0.5 - armAngle);
        ctx.fillRect(-3, 0, 6, 15);
        
        // Casting hand with magic
        ctx.fillStyle = '#FFE4C4';
        ctx.beginPath();
        ctx.arc(0, 15, 4, 0, Math.PI * 2);
        ctx.fill();
        
        // Magic particles from hand
        ctx.fillStyle = '#00FFFF';
        for (let i = 0; i < 3; i++) {
            const particleAngle = (frame * 0.1 + i * 2) % (Math.PI * 2);
            const px = Math.cos(particleAngle) * 8;
            const py = 15 + Math.sin(particleAngle) * 8;
            ctx.globalAlpha = 0.7;
            ctx.beginPath();
            ctx.arc(px, py, 2, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.globalAlpha = 1;
        ctx.restore();
        
        // Head
        ctx.fillStyle = '#FFE4C4';
        ctx.beginPath();
        ctx.arc(x, y - 25 + float, 10, 0, Math.PI * 2);
        ctx.fill();
        
        // Wizard hat
        ctx.fillStyle = '#4B0082';
        ctx.beginPath();
        ctx.moveTo(x - 12, y - 30 + float);
        ctx.lineTo(x, y - 55 + float);
        ctx.lineTo(x + 12, y - 30 + float);
        ctx.closePath();
        ctx.fill();
        
        // Hat brim
        ctx.fillRect(x - 15, y - 32 + float, 30, 4);
        
        // Hat stars
        ctx.fillStyle = '#FFD700';
        ctx.save();
        ctx.translate(x, y - 42 + float);
        ctx.scale(0.4, 0.4);
        this.drawStar(ctx, 0, 0, 5, 3, 2);
        ctx.restore();
        
        // Beard
        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.moveTo(x - 8, y - 20 + float);
        ctx.quadraticCurveTo(x, y - 10 + float, x + 8, y - 20 + float);
        ctx.lineTo(x + 6, y - 5 + float);
        ctx.lineTo(x, y + float);
        ctx.lineTo(x - 6, y - 5 + float);
        ctx.closePath();
        ctx.fill();
        
        // Eyes
        ctx.fillStyle = '#000';
        ctx.beginPath();
        ctx.arc(x - 4, y - 28 + float, 1, 0, Math.PI * 2);
        ctx.arc(x + 4, y - 28 + float, 1, 0, Math.PI * 2);
        ctx.fill();
        
        // Staff
        ctx.strokeStyle = '#8B4513';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(x + 15 * (facingLeft ? -1 : 1), y + 25 + float);
        ctx.lineTo(x + 20 * (facingLeft ? -1 : 1), y - 40 + float);
        ctx.stroke();
        
        // Crystal on staff
        ctx.fillStyle = '#00CED1';
        ctx.save();
        ctx.translate(x + 20 * (facingLeft ? -1 : 1), y - 45 + float);
        ctx.rotate(frame * 0.05);
        ctx.beginPath();
        ctx.moveTo(0, -8);
        ctx.lineTo(-6, 0);
        ctx.lineTo(0, 8);
        ctx.lineTo(6, 0);
        ctx.closePath();
        ctx.fill();
        
        // Crystal glow
        ctx.shadowBlur = 20;
        ctx.shadowColor = '#00CED1';
        ctx.fill();
        ctx.restore();
    }

    drawStar(ctx, cx, cy, outerRadius, innerRadius, points) {
        let angle = -Math.PI / 2;
        const step = Math.PI / points;
        
        ctx.beginPath();
        for (let i = 0; i < points * 2; i++) {
            const radius = i % 2 === 0 ? outerRadius : innerRadius;
            const x = cx + Math.cos(angle) * radius;
            const y = cy + Math.sin(angle) * radius;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
            angle += step;
        }
        ctx.closePath();
        ctx.fill();
    }
}

// Enhanced Stage Backgrounds
class StageRenderer {
    constructor() {
        this.parallaxLayers = {
            forest: this.createForestLayers(),
            cave: this.createCaveLayers(),
            castle: this.createCastleLayers()
        };
    }

    createForestLayers() {
        return {
            far: (ctx, offset, canvas) => {
                // Sky gradient
                const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
                gradient.addColorStop(0, '#87CEEB');
                gradient.addColorStop(0.5, '#98D8E8');
                gradient.addColorStop(1, '#C0E8F0');
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                // Distant mountains
                ctx.fillStyle = '#8B9DC3';
                ctx.beginPath();
                ctx.moveTo(0, canvas.height * 0.6);
                for (let x = 0; x <= canvas.width + 200; x += 200) {
                    ctx.quadraticCurveTo(
                        x - offset * 0.1 + 50, canvas.height * 0.4,
                        x - offset * 0.1 + 100, canvas.height * 0.6
                    );
                }
                ctx.lineTo(canvas.width, canvas.height);
                ctx.lineTo(0, canvas.height);
                ctx.fill();
            },
            mid: (ctx, offset, canvas, time) => {
                // Trees layer 1
                ctx.fillStyle = '#2d5f2d';
                for (let x = -200; x <= canvas.width + 200; x += 150) {
                    const treeX = x - offset * 0.3;
                    const sway = Math.sin(time * 0.001 + x) * 3;
                    this.drawTree(ctx, treeX + sway, canvas.height * 0.7, 80, '#2d5f2d');
                }
            },
            near: (ctx, offset, canvas, time) => {
                // Trees layer 2
                ctx.fillStyle = '#1a3d1a';
                for (let x = -100; x <= canvas.width + 200; x += 100) {
                    const treeX = x - offset * 0.5;
                    const sway = Math.sin(time * 0.001 + x * 2) * 5;
                    this.drawTree(ctx, treeX + sway, canvas.height * 0.8, 100, '#1a3d1a');
                }
                
                // Grass and flowers
                for (let x = 0; x <= canvas.width; x += 20) {
                    const grassX = x - (offset * 0.6) % 20;
                    const grassHeight = 10 + Math.sin(x * 0.1) * 5;
                    
                    // Grass
                    ctx.strokeStyle = '#228B22';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(grassX, canvas.height - 30);
                    ctx.quadraticCurveTo(
                        grassX + Math.sin(time * 0.002 + x) * 3,
                        canvas.height - 30 - grassHeight,
                        grassX + Math.sin(time * 0.002 + x) * 5,
                        canvas.height - 30 - grassHeight * 2
                    );
                    ctx.stroke();
                    
                    // Occasional flowers
                    if (x % 60 === 0) {
                        ctx.fillStyle = ['#FF69B4', '#FFD700', '#FF6347'][Math.floor(x / 60) % 3];
                        ctx.beginPath();
                        ctx.arc(grassX + 5, canvas.height - 40, 3, 0, Math.PI * 2);
                        ctx.fill();
                    }
                }
            }
        };
    }

    createCaveLayers() {
        return {
            far: (ctx, offset, canvas) => {
                // Dark cave background
                const gradient = ctx.createRadialGradient(
                    canvas.width / 2, canvas.height / 2, 100,
                    canvas.width / 2, canvas.height / 2, canvas.width
                );
                gradient.addColorStop(0, '#1a1a2e');
                gradient.addColorStop(1, '#0a0a0f');
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                // Distant crystals glow
                ctx.shadowBlur = 30;
                for (let i = 0; i < 5; i++) {
                    const x = (i * 200 - offset * 0.1) % canvas.width;
                    const y = 100 + Math.sin(i) * 50;
                    ctx.shadowColor = ['#00CED1', '#9370DB', '#FF69B4'][i % 3];
                    ctx.fillStyle = ctx.shadowColor;
                    ctx.beginPath();
                    ctx.arc(x, y, 3, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.shadowBlur = 0;
            },
            mid: (ctx, offset, canvas, time) => {
                // Stalactites
                ctx.fillStyle = '#2c2c3e';
                for (let x = -100; x <= canvas.width + 100; x += 80) {
                    const stalX = x - offset * 0.3;
                    this.drawStalactite(ctx, stalX, 0, 30 + Math.sin(x) * 20, 100 + Math.sin(x * 2) * 50);
                }
                
                // Crystals
                for (let i = 0; i < 8; i++) {
                    const x = (i * 150 - offset * 0.4) % (canvas.width + 300) - 150;
                    const y = canvas.height * 0.7 + Math.sin(i * 2) * 100;
                    const color = ['#00CED1', '#9370DB', '#FF69B4'][i % 3];
                    this.drawCrystal(ctx, x, y, 20, color, time + i * 1000);
                }
            },
            near: (ctx, offset, canvas, time) => {
                // Stalagmites
                ctx.fillStyle = '#1a1a2e';
                for (let x = -50; x <= canvas.width + 50; x += 60) {
                    const stagX = x - offset * 0.5;
                    this.drawStalagmite(ctx, stagX, canvas.height, 25 + Math.sin(x * 2) * 15, 80 + Math.sin(x) * 40);
                }
                
                // Glowing mushrooms
                for (let i = 0; i < 10; i++) {
                    const x = (i * 100 - offset * 0.6) % (canvas.width + 200) - 100;
                    const y = canvas.height - 40;
                    this.drawGlowingMushroom(ctx, x, y, 15, time + i * 500);
                }
            }
        };
    }

    createCastleLayers() {
        return {
            far: (ctx, offset, canvas) => {
                // Twilight sky
                const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
                gradient.addColorStop(0, '#1a0033');
                gradient.addColorStop(0.3, '#330066');
                gradient.addColorStop(0.6, '#4B0082');
                gradient.addColorStop(1, '#663399');
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                // Moon
                ctx.fillStyle = '#F0E68C';
                ctx.shadowBlur = 30;
                ctx.shadowColor = '#F0E68C';
                ctx.beginPath();
                ctx.arc(canvas.width * 0.8, 100, 40, 0, Math.PI * 2);
                ctx.fill();
                ctx.shadowBlur = 0;
                
                // Stars
                ctx.fillStyle = '#FFFFFF';
                for (let i = 0; i < 50; i++) {
                    const x = (i * 73) % canvas.width;
                    const y = (i * 37) % (canvas.height * 0.5);
                    const size = 0.5 + (i % 3) * 0.5;
                    ctx.beginPath();
                    ctx.arc(x, y, size, 0, Math.PI * 2);
                    ctx.fill();
                }
            },
            mid: (ctx, offset, canvas, time) => {
                // Castle towers
                ctx.fillStyle = '#36454F';
                for (let i = 0; i < 4; i++) {
                    const x = i * 300 - offset * 0.3;
                    const height = 200 + Math.sin(i) * 50;
                    this.drawCastleTower(ctx, x, canvas.height - height, 80, height);
                }
                
                // Flying bats
                ctx.fillStyle = '#000000';
                for (let i = 0; i < 5; i++) {
                    const batX = ((time * 0.1 + i * 200) - offset * 0.4) % (canvas.width + 100) - 50;
                    const batY = 150 + Math.sin(time * 0.003 + i) * 50;
                    this.drawBat(ctx, batX, batY, time);
                }
            },
            near: (ctx, offset, canvas, time) => {
                // Castle walls
                ctx.fillStyle = '#2C3E50';
                const wallHeight = 150;
                ctx.fillRect(0, canvas.height - wallHeight, canvas.width, wallHeight);
                
                // Battlements
                for (let x = 0; x < canvas.width + 40; x += 40) {
                    ctx.fillRect(x - offset * 0.5 % 40, canvas.height - wallHeight - 20, 25, 20);
                }
                
                // Torches
                for (let i = 0; i < 8; i++) {
                    const torchX = (i * 150 - offset * 0.6) % (canvas.width + 300) - 150;
                    const torchY = canvas.height - wallHeight + 20;
                    this.drawTorch(ctx, torchX, torchY, time + i * 300);
                }
                
                // Banners
                for (let i = 0; i < 6; i++) {
                    const bannerX = (i * 200 - offset * 0.6) % (canvas.width + 400) - 200;
                    const bannerY = canvas.height - wallHeight - 50;
                    this.drawBanner(ctx, bannerX, bannerY, ['#FF0000', '#0000FF', '#FFD700'][i % 3], time);
                }
            }
        };
    }

    drawTree(ctx, x, y, size, color) {
        // Trunk
        ctx.fillStyle = '#654321';
        ctx.fillRect(x - size * 0.1, y - size * 0.4, size * 0.2, size * 0.4);
        
        // Leaves
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(x, y - size);
        ctx.lineTo(x - size * 0.5, y - size * 0.3);
        ctx.lineTo(x + size * 0.5, y - size * 0.3);
        ctx.closePath();
        ctx.fill();
        
        ctx.beginPath();
        ctx.moveTo(x, y - size * 0.8);
        ctx.lineTo(x - size * 0.4, y - size * 0.5);
        ctx.lineTo(x + size * 0.4, y - size * 0.5);
        ctx.closePath();
        ctx.fill();
    }

    drawStalactite(ctx, x, y, width, height) {
        ctx.beginPath();
        ctx.moveTo(x - width/2, y);
        ctx.lineTo(x + width/2, y);
        ctx.lineTo(x, y + height);
        ctx.closePath();
        ctx.fill();
    }

    drawStalagmite(ctx, x, y, width, height) {
        ctx.beginPath();
        ctx.moveTo(x - width/2, y);
        ctx.lineTo(x + width/2, y);
        ctx.lineTo(x, y - height);
        ctx.closePath();
        ctx.fill();
    }

    drawCrystal(ctx, x, y, size, color, time) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(Math.sin(time * 0.001) * 0.1);
        
        // Crystal glow
        ctx.shadowBlur = 20;
        ctx.shadowColor = color;
        
        // Crystal body
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.8;
        ctx.beginPath();
        ctx.moveTo(0, -size);
        ctx.lineTo(-size * 0.3, -size * 0.3);
        ctx.lineTo(-size * 0.2, size * 0.5);
        ctx.lineTo(size * 0.2, size * 0.5);
        ctx.lineTo(size * 0.3, -size * 0.3);
        ctx.closePath();
        ctx.fill();
        
        // Inner glow
        ctx.fillStyle = '#FFFFFF';
        ctx.globalAlpha = 0.4;
        ctx.beginPath();
        ctx.moveTo(0, -size * 0.8);
        ctx.lineTo(-size * 0.1, -size * 0.4);
        ctx.lineTo(size * 0.1, -size * 0.4);
        ctx.closePath();
        ctx.fill();
        
        ctx.restore();
    }

    drawGlowingMushroom(ctx, x, y, size, time) {
        // Stem
        ctx.fillStyle = '#D3D3D3';
        ctx.fillRect(x - size * 0.2, y - size, size * 0.4, size);
        
        // Cap
        ctx.save();
        ctx.shadowBlur = 15;
        ctx.shadowColor = '#00FF00';
        ctx.fillStyle = '#00FF00';
        ctx.globalAlpha = 0.7 + Math.sin(time * 0.003) * 0.3;
        ctx.beginPath();
        ctx.arc(x, y - size, size * 0.8, Math.PI, 0, true);
        ctx.closePath();
        ctx.fill();
        
        // Spots
        ctx.fillStyle = '#00CC00';
        ctx.globalAlpha = 1;
        ctx.beginPath();
        ctx.arc(x - size * 0.3, y - size * 1.2, size * 0.1, 0, Math.PI * 2);
        ctx.arc(x + size * 0.2, y - size * 1.1, size * 0.1, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    drawCastleTower(ctx, x, y, width, height) {
        // Tower body
        ctx.fillStyle = '#36454F';
        ctx.fillRect(x, y, width, height);
        
        // Tower details
        ctx.strokeStyle = '#2C3E50';
        ctx.lineWidth = 2;
        for (let i = 0; i < height / 30; i++) {
            ctx.strokeRect(x + 5, y + i * 30, width - 10, 20);
        }
        
        // Tower top
        ctx.fillStyle = '#8B0000';
        ctx.beginPath();
        ctx.moveTo(x - 10, y);
        ctx.lineTo(x + width / 2, y - 40);
        ctx.lineTo(x + width + 10, y);
        ctx.closePath();
        ctx.fill();
        
        // Windows
        ctx.fillStyle = '#FFD700';
        for (let i = 0; i < 3; i++) {
            const windowY = y + 30 + i * 60;
            if (windowY < y + height - 30) {
                ctx.beginPath();
                ctx.arc(x + width / 2, windowY, 8, Math.PI, 0, true);
                ctx.rect(x + width / 2 - 8, windowY, 16, 8);
                ctx.fill();
            }
        }
    }

    drawBat(ctx, x, y, time) {
        const flap = Math.sin(time * 0.01) * 0.3;
        
        // Body
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fill();
        
        // Wings
        ctx.beginPath();
        ctx.moveTo(x - 5, y);
        ctx.quadraticCurveTo(x - 15, y - 5 + flap * 10, x - 20, y);
        ctx.quadraticCurveTo(x - 15, y + 3, x - 5, y + 2);
        ctx.moveTo(x + 5, y);
        ctx.quadraticCurveTo(x + 15, y - 5 - flap * 10, x + 20, y);
        ctx.quadraticCurveTo(x + 15, y + 3, x + 5, y + 2);
        ctx.fill();
    }

    drawTorch(ctx, x, y, time) {
        // Torch holder
        ctx.fillStyle = '#654321';
        ctx.fillRect(x - 3, y, 6, 20);
        
        // Fire
        const flicker = Math.sin(time * 0.01) * 2;
        ctx.save();
        ctx.shadowBlur = 20;
        ctx.shadowColor = '#FFA500';
        
        // Outer flame
        ctx.fillStyle = '#FF6347';
        ctx.beginPath();
        ctx.moveTo(x, y - 5);
        ctx.quadraticCurveTo(x - 8 + flicker, y - 15, x, y - 25);
        ctx.quadraticCurveTo(x + 8 - flicker, y - 15, x, y - 5);
        ctx.fill();
        
        // Inner flame
        ctx.fillStyle = '#FFD700';
        ctx.beginPath();
        ctx.moveTo(x, y - 5);
        ctx.quadraticCurveTo(x - 4 + flicker * 0.5, y - 10, x, y - 15);
        ctx.quadraticCurveTo(x + 4 - flicker * 0.5, y - 10, x, y - 5);
        ctx.fill();
        
        ctx.restore();
    }

    drawBanner(ctx, x, y, color, time) {
        const wave = Math.sin(time * 0.002 + x * 0.01) * 3;
        
        // Pole
        ctx.strokeStyle = '#654321';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x, y + 80);
        ctx.stroke();
        
        // Banner
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.moveTo(x + 2, y + 10);
        ctx.quadraticCurveTo(x + 20 + wave, y + 20, x + 25 + wave * 1.5, y + 40);
        ctx.lineTo(x + 20 + wave * 1.2, y + 50);
        ctx.lineTo(x + 15 + wave * 0.8, y + 45);
        ctx.lineTo(x + 10 + wave * 0.5, y + 50);
        ctx.lineTo(x + 2, y + 40);
        ctx.closePath();
        ctx.fill();
        
        // Banner emblem
        ctx.fillStyle = color === '#FF0000' ? '#FFD700' : '#FFFFFF';
        ctx.save();
        ctx.translate(x + 12 + wave * 0.7, y + 25);
        ctx.scale(0.5, 0.5);
        const renderer = new AdvancedEnemyRenderer();
        renderer.drawStar(ctx, 0, 0, 8, 4, 4);
        ctx.restore();
    }

    render(ctx, canvas, stage, cameraX, time) {
        const layers = this.parallaxLayers[stage];
        if (!layers) return;
        
        // Draw all parallax layers
        layers.far(ctx, cameraX, canvas, time);
        layers.mid(ctx, cameraX, canvas, time);
        layers.near(ctx, cameraX, canvas, time);
    }
}

// Main Menu Animation System
class MainMenuAnimations {
    constructor() {
        this.particles = [];
        this.time = 0;
    }

    update(deltaTime) {
        this.time += deltaTime;
        
        // Add new particles
        if (Math.random() < 0.1) {
            this.particles.push({
                x: Math.random() * 800,
                y: 600,
                vx: (Math.random() - 0.5) * 50,
                vy: -100 - Math.random() * 100,
                size: 2 + Math.random() * 3,
                color: `hsl(${Math.random() * 60 + 30}, 100%, 70%)`,
                life: 2,
                type: Math.random() < 0.5 ? 'star' : 'circle'
            });
        }
        
        // Update particles
        this.particles = this.particles.filter(p => {
            p.x += p.vx * deltaTime / 1000;
            p.y += p.vy * deltaTime / 1000;
            p.life -= deltaTime / 1000;
            p.vy += 50 * deltaTime / 1000;
            return p.life > 0;
        });
    }

    render(ctx, canvas) {
        // Animated background
        const gradient = ctx.createRadialGradient(
            canvas.width / 2, canvas.height / 2, 0,
            canvas.width / 2, canvas.height / 2, canvas.width
        );
        gradient.addColorStop(0, '#1a1a2e');
        gradient.addColorStop(0.5, '#16213e');
        gradient.addColorStop(1, '#0f3460');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Animated grid
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.lineWidth = 1;
        for (let x = 0; x < canvas.width; x += 50) {
            const offset = Math.sin(this.time * 0.001 + x * 0.01) * 10;
            ctx.beginPath();
            ctx.moveTo(x + offset, 0);
            ctx.lineTo(x + offset, canvas.height);
            ctx.stroke();
        }
        
        for (let y = 0; y < canvas.height; y += 50) {
            const offset = Math.cos(this.time * 0.001 + y * 0.01) * 10;
            ctx.beginPath();
            ctx.moveTo(0, y + offset);
            ctx.lineTo(canvas.width, y + offset);
            ctx.stroke();
        }
        
        // Particles
        this.particles.forEach(p => {
            ctx.save();
            ctx.globalAlpha = p.life / 2;
            ctx.fillStyle = p.color;
            
            if (p.type === 'star') {
                ctx.translate(p.x, p.y);
                ctx.rotate(this.time * 0.002);
                const renderer = new AdvancedEnemyRenderer();
                renderer.drawStar(ctx, 0, 0, p.size, p.size * 0.5, 5);
            } else {
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.restore();
        });
        
        // Title with glow effect
        ctx.save();
        ctx.shadowBlur = 20;
        ctx.shadowColor = '#FFD700';
        ctx.fillStyle = '#FFD700';
        ctx.font = 'bold 64px Arial';
        ctx.textAlign = 'center';
        const titleY = 150 + Math.sin(this.time * 0.002) * 10;
        ctx.fillText('RETRO PLATFORMER', canvas.width / 2, titleY);
        
        // Subtitle
        ctx.shadowBlur = 10;
        ctx.font = '24px Arial';
        ctx.fillStyle = '#FFFFFF';
        ctx.fillText('Ultimate Edition', canvas.width / 2, titleY + 40);
        ctx.restore();
    }

    renderButton(ctx, text, x, y, width, height, isSelected) {
        // Button glow
        if (isSelected) {
            ctx.save();
            ctx.shadowBlur = 20;
            ctx.shadowColor = '#00CED1';
            ctx.fillStyle = 'rgba(0, 206, 209, 0.2)';
            ctx.fillRect(x - 10, y - 10, width + 20, height + 20);
            ctx.restore();
        }
        
        // Button background
        const gradient = ctx.createLinearGradient(x, y, x, y + height);
        gradient.addColorStop(0, isSelected ? '#2E8B57' : '#1a1a1a');
        gradient.addColorStop(1, isSelected ? '#228B22' : '#0a0a0a');
        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, width, height);
        
        // Button border
        ctx.strokeStyle = isSelected ? '#00CED1' : '#444444';
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, width, height);
        
        // Button text
        ctx.fillStyle = isSelected ? '#FFFFFF' : '#AAAAAA';
        ctx.font = 'bold 24px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, x + width / 2, y + height / 2);
        
        // Selection arrows
        if (isSelected) {
            const arrowOffset = Math.sin(this.time * 0.003) * 5;
            ctx.fillStyle = '#FFD700';
            
            // Left arrow
            ctx.beginPath();
            ctx.moveTo(x - 30 + arrowOffset, y + height / 2);
            ctx.lineTo(x - 20 + arrowOffset, y + height / 2 - 10);
            ctx.lineTo(x - 20 + arrowOffset, y + height / 2 + 10);
            ctx.closePath();
            ctx.fill();
            
            // Right arrow
            ctx.beginPath();
            ctx.moveTo(x + width + 30 - arrowOffset, y + height / 2);
            ctx.lineTo(x + width + 20 - arrowOffset, y + height / 2 - 10);
            ctx.lineTo(x + width + 20 - arrowOffset, y + height / 2 + 10);
            ctx.closePath();
            ctx.fill();
        }
    }
}

// Export all systems
window.AdvancedGraphics = AdvancedGraphics;
window.AdvancedEnemyRenderer = AdvancedEnemyRenderer;
window.StageRenderer = StageRenderer;
window.MainMenuAnimations = MainMenuAnimations;