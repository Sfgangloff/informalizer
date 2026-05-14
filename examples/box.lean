import Mathlib.Data.Fin.Basic
import Mathlib.Data.Fintype.Basic
import Mathlib.Data.Fintype.Pi
import Mathlib.Data.Fintype.BigOperators
import Mathlib.Data.Int.Interval
import Mathlib.Data.Finset.Lattice.Fold
import dependencies.Subshift

/-! # Discrete cubes in `ℤ^d`

Cardinality, monotonicity and base-`n` indexing for the asymmetric cube
`box d n = {0,...,n-1}^d`, the symmetric cube `symBox d n = {-n,...,n}^d`,
and bijections `↥(box d n) ≃ (Fin d → Fin n) ≃ Fin (n^d)` used for
encoding patterns as natural numbers.

Originally lived in `papers/HochmanMeyerovitch/HochmanMeyerovitch.lean`;
moved here for reuse across papers. The definition of `box` itself
lives in `dependencies/Subshift.lean`.
-/

/-! ## Cardinality and monotonicity of `box d n` -/

@[simp]
theorem box_card (d n : ℕ) : (box d n).card = n ^ d := by
  simp [box, Fintype.card_piFinset, Int.card_Ico]

theorem box_mono {d m n : ℕ} (hmn : m ≤ n) : box d m ⊆ box d n :=
  Fintype.piFinset_subset _ _ (fun _ => Finset.Ico_subset_Ico_right (by exact_mod_cast hmn))

theorem box_zero {d : ℕ} (hd : 0 < d) : box d 0 = ∅ := by
  haveI : Nonempty (Fin d) := ⟨⟨0, hd⟩⟩
  simp [box]

/-! ## Bijections `↥(box d n) ≃ (Fin d → Fin n) ≃ Fin (n^d)` -/

/-- The subtype of elements in `box d n` is in computable bijection with `Fin d → Fin n`. -/
def boxFnEquiv (d n : ℕ) : ↥(box d n) ≃ (Fin d → Fin n) where
  toFun v := fun j =>
    ⟨(v.val j).toNat, by
      have hv := v.property
      simp only [box, Fintype.mem_piFinset, Finset.mem_Ico] at hv
      obtain ⟨h1, h2⟩ := hv j
      have : (v.val j).toNat < n := by
        have h2' : v.val j < (n : ℤ) := h2
        have hnn : (0 : ℤ) ≤ v.val j := h1
        rw [Int.toNat_lt hnn]
        exact_mod_cast h2
      exact this⟩
  invFun f :=
    ⟨fun j => ((f j).val : ℤ), by
      simp only [box, Fintype.mem_piFinset, Finset.mem_Ico]
      intro j
      refine ⟨Int.natCast_nonneg _, ?_⟩
      exact_mod_cast (f j).is_lt⟩
  left_inv v := by
    ext j
    have hv := v.property
    simp only [box, Fintype.mem_piFinset, Finset.mem_Ico] at hv
    obtain ⟨h1, _⟩ := hv j
    show ((v.val j).toNat : ℤ) = v.val j
    exact Int.toNat_of_nonneg h1
  right_inv f := by
    ext j
    show (((f j).val : ℤ)).toNat = (f j).val
    simp

/-- `↥(box d n) ≃ Fin (n^d)` via base-n digit composition with `finFunctionFinEquiv`. -/
def boxIxEquiv (d n : ℕ) : ↥(box d n) ≃ Fin (n^d) :=
  (boxFnEquiv d n).trans finFunctionFinEquiv

/-- `Pattern α (box d n) ≃ (Fin (n^d) → α)` — bridges the dependent-Pattern type
to a uniform-shape function type, useful for transferring computability arguments. -/
def patternFnEquiv (α : Type*) (d n : ℕ) : Pattern α (box d n) ≃ (Fin (n^d) → α) :=
  Equiv.arrowCongr (boxIxEquiv d n) (Equiv.refl α)

/-- Cardinality formula via the uniform-shape bridge: `|Pattern α (box d n)| = |α|^(n^d)`. -/
theorem fintype_card_pattern_eq {α : Type*} [Fintype α] (d n : ℕ) :
    Fintype.card (Pattern α (box d n)) = (Fintype.card α) ^ (n ^ d) := by
  rw [Fintype.card_congr (patternFnEquiv α d n)]
  simp

/-! ## Base-`n` enumeration of `box d n` -/

/-- The `i`-th element of `box d n` under the canonical base-`n` digit enumeration. -/
def boxIndex (d n i : ℕ) : Lat d :=
  fun j : Fin d => ((i / n ^ j.val) % n : ℤ)

theorem boxIndex_mem {d n i : ℕ} (hi : i < n ^ d) : boxIndex d n i ∈ box d n := by
  simp only [box, Fintype.mem_piFinset, Finset.mem_Ico]
  intro j
  have hn_pos : 0 < n := by
    rcases Nat.eq_zero_or_pos n with hn | hn
    · subst hn
      have hd_pos : 0 < d := j.pos
      rw [zero_pow hd_pos.ne'] at hi
      exact absurd hi (Nat.not_lt_zero _)
    · exact hn
  show 0 ≤ ((i / n ^ j.val) % n : ℤ) ∧ ((i / n ^ j.val) % n : ℤ) < (n : ℤ)
  refine ⟨Int.natCast_nonneg _, ?_⟩
  exact_mod_cast Nat.mod_lt _ hn_pos

/-- The inverse-direction index map: `w ∈ box d n` maps to its base-n index in `Fin (n^d)`. -/
def boxIndexInv (d n : ℕ) (w : Lat d) : ℕ :=
  Finset.univ.sum (fun j : Fin d => (w j).toNat * n ^ j.val)

/-- `boxIxEquiv` agrees with `boxIndexInv` on box elements. -/
theorem boxIxEquiv_val (d n : ℕ) (v : ↥(box d n)) :
    (boxIxEquiv d n v).val = boxIndexInv d n v.val := by
  unfold boxIxEquiv boxIndexInv boxFnEquiv
  rw [Equiv.trans_apply, finFunctionFinEquiv_apply]
  rfl

/-- `boxIxEquiv.symm` agrees with `boxIndex` on `Fin (n^d)` indices. -/
theorem boxIxEquiv_symm_val (d n : ℕ) (i : Fin (n^d)) :
    ((boxIxEquiv d n).symm i).val = boxIndex d n i.val := by
  unfold boxIxEquiv boxIndex boxFnEquiv
  funext j
  rfl

/-- Round-trip: `boxIndex (boxIndexInv w) = w` for `w ∈ box d n`. -/
theorem boxIndex_boxIndexInv {d n : ℕ} {w : Lat d} (hw : w ∈ box d n) :
    boxIndex d n (boxIndexInv d n w) = w := by
  have hroundtrip : ((boxIxEquiv d n).symm (boxIxEquiv d n ⟨w, hw⟩)) = ⟨w, hw⟩ :=
    Equiv.symm_apply_apply _ _
  have h1 : ((boxIxEquiv d n).symm (boxIxEquiv d n ⟨w, hw⟩)).val = w := by
    rw [hroundtrip]
  rw [boxIxEquiv_symm_val, boxIxEquiv_val] at h1
  exact h1

/-- Round-trip: `boxIndexInv (boxIndex i) = i` for `i : Fin (n^d)`. -/
theorem boxIndexInv_boxIndex {d n : ℕ} (i : Fin (n^d)) :
    boxIndexInv d n (boxIndex d n i.val) = i.val := by
  have hroundtrip : (boxIxEquiv d n) ((boxIxEquiv d n).symm i) = i :=
    Equiv.apply_symm_apply _ _
  have h1 : ((boxIxEquiv d n) ((boxIxEquiv d n).symm i)).val = i.val := by
    rw [hroundtrip]
  rw [boxIxEquiv_val, boxIxEquiv_symm_val] at h1
  exact h1

/-! ## Symmetric cube `symBox d n = {-n,...,n}^d` -/

/-- The symmetric cube `Q_n = {-n,...,n}^d ⊆ ℤ^d`. -/
def symBox (d n : ℕ) : Finset (Lat d) :=
  Fintype.piFinset (fun _ : Fin d => Finset.Icc (-(n : ℤ)) (n : ℤ))

@[simp]
theorem symBox_card (d n : ℕ) : (symBox d n).card = (2 * n + 1) ^ d := by
  simp only [symBox, Fintype.card_piFinset, Int.card_Icc]
  have h_each : ((n : ℤ) + 1 + (n : ℤ)).toNat = 2 * n + 1 := by
    have heq : ((n : ℤ) + 1 + (n : ℤ)) = ((2 * n + 1 : ℕ) : ℤ) := by push_cast; ring
    rw [heq, Int.toNat_natCast]
  rw [Finset.prod_const]
  simp [h_each]

theorem symBox_mono {d m n : ℕ} (hmn : m ≤ n) : symBox d m ⊆ symBox d n :=
  Fintype.piFinset_subset _ _ (fun _ => Finset.Icc_subset_Icc
    (by exact_mod_cast neg_le_neg (by exact_mod_cast hmn))
    (by exact_mod_cast hmn))

theorem box_subset_symBox {d n : ℕ} : box d (n + 1) ⊆ symBox d n := by
  intro u hu
  simp only [box, symBox, Fintype.mem_piFinset, Finset.mem_Ico, Finset.mem_Icc] at hu ⊢
  intro i
  obtain ⟨h1, h2⟩ := hu i
  refine ⟨?_, ?_⟩
  · have : -(n : ℤ) ≤ 0 := by linarith [Int.natCast_nonneg n]
    linarith
  · push_cast at h2
    linarith

theorem symBox_disjoint_sdiff {d k r N : ℕ} :
    Disjoint (symBox d k) (symBox d N \ symBox d (k + r)) := by
  apply Finset.disjoint_left.mpr
  intro x hxk hxN
  exact (Finset.mem_sdiff.mp hxN).2 (symBox_mono (Nat.le_add_right k r) hxk)

/-- For `u ∈ Q_k` and `v ∈ Q_N \ Q_{k+r}`, the supremum-norm distance is at least `r + 1`. -/
theorem Lat.supNorm_sub_ge_of_inner_outer {d k r N : ℕ}
    (u v : Lat d) (hu : u ∈ symBox d k) (hv : v ∈ symBox d N \ symBox d (k + r)) :
    (r + 1 : ℤ) ≤ Lat.supNorm (v - u) := by
  obtain ⟨_, hvNotKr⟩ := Finset.mem_sdiff.mp hv
  have h_exists : ∃ i, (k + r : ℤ) < |v i| := by
    by_contra h_all
    push_neg at h_all
    apply hvNotKr
    simp only [symBox, Fintype.mem_piFinset, Finset.mem_Icc]
    intro i
    have hi := h_all i
    rw [abs_le] at hi
    push_cast
    exact hi
  obtain ⟨i, hi⟩ := h_exists
  simp only [symBox, Fintype.mem_piFinset, Finset.mem_Icc] at hu
  obtain ⟨hu_l, hu_h⟩ := hu i
  have hu_abs : |u i| ≤ (k : ℤ) := abs_le.mpr ⟨hu_l, hu_h⟩
  have h_diff : (r + 1 : ℤ) ≤ |v i - u i| := by
    have h1 : |v i| - |u i| ≤ |v i - u i| := abs_sub_abs_le_abs_sub _ _
    linarith
  have h_natabs_eq : (v i - u i).natAbs = |v i - u i|.toNat := by
    rw [Int.abs_eq_natAbs, Int.toNat_natCast]
  have h_natabs_ge : (r + 1 : ℕ) ≤ (v i - u i).natAbs := by
    have hnn : 0 ≤ |v i - u i| := abs_nonneg _
    have h_cast : ((v i - u i).natAbs : ℤ) = |v i - u i| := by
      rw [Int.abs_eq_natAbs]
    have : ((r + 1 : ℕ) : ℤ) ≤ ((v i - u i).natAbs : ℤ) := by rw [h_cast]; exact_mod_cast h_diff
    exact_mod_cast this
  unfold Lat.supNorm
  have h_sup_ge : (v i - u i).natAbs ≤ Finset.univ.sup (fun j => ((v - u) j).natAbs) := by
    have h := Finset.le_sup (s := Finset.univ) (f := fun j => ((v - u) j).natAbs)
      (Finset.mem_univ i)
    show ((v - u) i).natAbs ≤ _
    exact h
  exact_mod_cast Nat.le_trans h_natabs_ge h_sup_ge
