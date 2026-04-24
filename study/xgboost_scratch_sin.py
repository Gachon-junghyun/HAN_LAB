import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

np.random.seed(42)
# sin 데이터
X = np.linspace(0, 4 * np.pi, 120)
y = np.sin(X) + 0.5 * np.sin(3 * X) + np.random.normal(0, 0.15, 120)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ── 트리 구현 ──────────────────────────────
class TreeNode:
    def __init__(self):
        self.split_value = None
        self.left = None
        self.right = None
        self.leaf_value = None

def calc_leaf_value(g, h, lam):
    return -np.sum(g) / (np.sum(h) + lam)

def calc_gain(g, h, lam):
    return (np.sum(g)**2) / (np.sum(h) + lam)

def build_tree(X, g, h, depth, max_depth, lam, min_samples):
    node = TreeNode()
    if depth >= max_depth or len(X) < min_samples:
        node.leaf_value = calc_leaf_value(g, h, lam)
        return node
    best_gain = -np.inf
    best_split = None
    for val in np.unique(X):
        lm = X < val
        rm = X >= val
        if lm.sum() < min_samples or rm.sum() < min_samples:
            continue
        gain = (calc_gain(g[lm], h[lm], lam)
              + calc_gain(g[rm], h[rm], lam)
              - calc_gain(g, h, lam))
        if gain > best_gain:
            best_gain = gain
            best_split = val
    if best_split is None or best_gain <= 0:
        node.leaf_value = calc_leaf_value(g, h, lam)
        return node
    node.split_value = best_split
    lm = X < best_split
    rm = X >= best_split
    node.left  = build_tree(X[lm], g[lm], h[lm], depth+1, max_depth, lam, min_samples)
    node.right = build_tree(X[rm], g[rm], h[rm], depth+1, max_depth, lam, min_samples)
    return node

def predict_tree(node, X):
    if node.leaf_value is not None:
        return np.full(len(X), node.leaf_value)
    preds = np.zeros(len(X))
    lm = X < node.split_value
    rm = X >= node.split_value
    if lm.sum() > 0: preds[lm] = predict_tree(node.left,  X[lm])
    if rm.sum() > 0: preds[rm] = predict_tree(node.right, X[rm])
    return preds

class XGBoostScratch:
    def __init__(self, n_rounds=30, lr=0.3, max_depth=4, lam=1.0, min_samples=2):
        self.n_rounds    = n_rounds
        self.lr          = lr
        self.max_depth   = max_depth
        self.lam         = lam
        self.min_samples = min_samples
        self.trees       = []
        self.F0          = None
        self.mse_log     = []

    def fit(self, X, y):
        self.F0 = np.mean(y)
        F = np.full(len(y), self.F0)
        for _ in range(self.n_rounds):
            g = -(y - F)
            h = np.ones(len(y))
            tree = build_tree(X, g, h, 0, self.max_depth, self.lam, self.min_samples)
            self.trees.append(tree)
            F = F + self.lr * predict_tree(tree, X)
            self.mse_log.append(np.mean((y - F)**2))

    def predict(self, X):
        F = np.full(len(X), self.F0)
        for tree in self.trees:
            F = F + self.lr * predict_tree(tree, X)
        return F

# ── 라운드별 스냅샷용 모델 ───────────────────────────────
snapshots = [1, 3, 10, 30]
models = {}
for n in snapshots:
    m = XGBoostScratch(n_rounds=n, lr=0.3, max_depth=4, lam=1.0)
    m.fit(X_train, y_train)
    models[n] = m

# MSE 로그는 30라운드 모델에서
full_model = models[30]

# ── 그래프 ───────────────────────────────────────────────
C_bg    = '#F8FAFC'
C_true  = '#CBD5E1'
C_train = '#2563EB'
C_test  = '#EF4444'
C_resid = '#EF4444'
colors  = ['#F59E0B', '#F97316', '#8B5CF6', '#10B981']

fig, axes = plt.subplots(2, 3, figsize=(16, 9), facecolor=C_bg)
fig.suptitle('XGBoost on sin wave  —  more rounds = smoother fit',
             fontsize=13, fontweight='bold', color='#1E293B', y=0.99)

X_fine = np.linspace(0, 4*np.pi, 500)
y_true_fine = np.sin(X_fine) + 0.5 * np.sin(3 * X_fine)

def style(ax, title):
    ax.set_facecolor('white')
    for sp in ax.spines.values():
        sp.set_color('#E2E8F0'); sp.set_linewidth(1.2)
    ax.set_title(title, fontsize=10, fontweight='bold', color='#334155', pad=7)
    ax.tick_params(colors='#64748B', labelsize=8)
    ax.grid(color='#F1F5F9', lw=0.8)

# 상단 4개: 라운드별 예측
for idx, n in enumerate(snapshots):
    row, col = divmod(idx, 3)
    ax = axes[row][col]
    style(ax, f'Round {n}')
    ax.plot(X_fine, y_true_fine, color=C_true, lw=1.5, ls='--', label='True curve', zorder=2)
    ax.scatter(X_train, y_train, color=C_train, s=20, alpha=0.5, zorder=3, label='Train')
    ax.scatter(X_test,  y_test,  color=C_test,  s=40, alpha=0.9, zorder=4, marker='*', label='Test')
    ax.plot(X_fine, models[n].predict(X_fine),
            color=colors[idx], lw=2.5, zorder=5, label=f'F{n}')
    test_mse = np.mean((y_test - models[n].predict(X_test))**2)
    ax.text(0.97, 0.05, f'Test MSE: {test_mse:.3f}',
            transform=ax.transAxes, ha='right', fontsize=9,
            fontweight='bold', color='#1E293B',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#F0FDF4', alpha=0.95))
    ax.legend(fontsize=7.5, framealpha=0.9, loc='upper right')
    ax.set_ylim(-2.2, 2.2)

# 우측 상단: 잔차 분포 비교
ax_r = axes[0][2]
style(ax_r, 'Residual distribution per round')
for idx, n in enumerate(snapshots):
    resid = y_test - models[n].predict(X_test)
    ax_r.hist(resid, bins=15, alpha=0.5, color=colors[idx],
              label=f'Round {n}', edgecolor='white')
ax_r.axvline(0, color='#475569', lw=1.5)
ax_r.set_xlabel('Residual', fontsize=8, color='#64748B')
ax_r.legend(fontsize=8)

# 하단 우측: MSE 감소 곡선
ax_m = axes[1][2]
style(ax_m, 'MSE per round  (train)')
ax_m.plot(range(1, 31), full_model.mse_log,
          'o-', color='#7C3AED', lw=2.2, ms=4, markevery=3)
ax_m.fill_between(range(1, 31), full_model.mse_log, alpha=0.1, color='#7C3AED')
for n, c in zip(snapshots, colors):
    ax_m.axvline(n, color=c, lw=1.5, ls=':', alpha=0.8)
    ax_m.text(n+0.3, max(full_model.mse_log)*0.85 - snapshots.index(n)*0.03,
              f'R{n}', color=c, fontsize=8, fontweight='bold')
ax_m.set_xlabel('Round', fontsize=8, color='#64748B')
ax_m.set_ylabel('MSE', fontsize=8, color='#64748B')

# 하단 중간: 오버피팅 확인 (train vs test mse)
ax_ov = axes[1][1]
style(ax_ov, 'Train vs Test MSE  (overfitting check)')
train_mses, test_mses = [], []
for n in range(1, 31):
    m = XGBoostScratch(n_rounds=n, lr=0.3, max_depth=4, lam=1.0)
    m.fit(X_train, y_train)
    train_mses.append(np.mean((y_train - m.predict(X_train))**2))
    test_mses.append(np.mean((y_test  - m.predict(X_test))**2))
ax_ov.plot(range(1,31), train_mses, 'o-', color='#2563EB', lw=2, ms=3, label='Train MSE')
ax_ov.plot(range(1,31), test_mses,  'o-', color='#EF4444', lw=2, ms=3, label='Test MSE')
best_round = np.argmin(test_mses) + 1
ax_ov.axvline(best_round, color='#10B981', lw=2, ls='--')
ax_ov.text(best_round+0.5, max(test_mses)*0.85,
           f'best\nround={best_round}', color='#10B981', fontsize=8.5, fontweight='bold')
ax_ov.set_xlabel('Round', fontsize=8, color='#64748B')
ax_ov.set_ylabel('MSE', fontsize=8, color='#64748B')
ax_ov.legend(fontsize=8.5)

# 하단 좌측: F0 기준선
ax_f0 = axes[1][0]
style(ax_f0, 'F0: just the mean  (starting point)')
ax_f0.plot(X_fine, y_true_fine, color=C_true, lw=1.5, ls='--', label='True curve')
ax_f0.scatter(X_train, y_train, color=C_train, s=20, alpha=0.5, label='Train')
ax_f0.axhline(np.mean(y_train), color='#9CA3AF', lw=2.5, label=f'F0 = {np.mean(y_train):.2f}')
for xi, yi in zip(X_train, y_train):
    ax_f0.plot([xi,xi], [np.mean(y_train), yi], color=C_resid, alpha=0.2, lw=0.8)
ax_f0.set_ylim(-2.2, 2.2)
ax_f0.legend(fontsize=7.5)
f0_mse = np.mean((y_train - np.mean(y_train))**2)
ax_f0.text(0.97, 0.05, f'MSE: {f0_mse:.3f}',
           transform=ax_f0.transAxes, ha='right', fontsize=9,
           fontweight='bold', color='#EF4444',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='#FEF2F2', alpha=0.95))

plt.tight_layout()
plt.savefig('xgb_sin.png', dpi=150, bbox_inches='tight', facecolor=C_bg)
print("done")
