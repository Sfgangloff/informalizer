# Informalizer Report: `example.lean`
_Generated on 2026-05-02_

## Summary

This Lean 4 file develops the foundational theory of **symbolic dynamics** — specifically, the study of subshifts over a group (or monoid) alphabet system — in a general algebraic and topological setting. The central objects are configurations (functions `G → A` from a group or monoid `G` to an alphabet `A`) and their topological and dynamical structure.

### Main Mathematical Objects

The file introduces several core structures. The **full shift** is the product space `G → A` with the Tychonoff (product) topology. A **subshift** ([`Subshift`](#obj-Subshift) / [`MulSubshift`](#obj-MulSubshift)) is a closed, shift-invariant subset of this space: closed in the product topology and invariant under all left-translation shifts `mulShift g` (where `mulShift g x = h ↦ x(g * h)`). The **cylinder sets** — collections of configurations agreeing with a fixed reference on a finite set of coordinates — serve as the basic open (and, for T1 alphabets, closed) sets of the product topology. **Patterns** ([`Pattern`](#obj-Pattern)) are finitely-supported partial configurations, encoding local constraints on configurations.

### Core Results

Key lemmas establish that cylinder sets are open when `A` carries the discrete topology and closed when `A` is T1. The file proves that the occurrence of a pattern at a position `g` — formalized via `mulOccursInAt` — is characterized as a cylinder set formed by the translated pattern, and that occurrence sets are open in the discrete topology. The shift operation is shown to interact cleanly with pattern occurrence: checking occurrence in a shifted configuration at position `h` is the same as checking occurrence in the original at position `g * h`.

### Construction of Subshifts from Forbidden Patterns

The main construction ([`mulForbidden`](#obj-mulForbidden), [`MulSubshift.ofForbidden`](#obj-MulSubshift-ofForbidden)) builds subshifts by specifying a family `F` of **forbidden patterns**: a configuration is allowed if and only if no pattern from `F` occurs at any position. The file proves this construction yields a legitimate subshift — the forbidden-pattern avoidance set is shift-invariant (since shifts commute with occurrence) and closed (as it is an intersection of complements of open occurrence sets). The **language** of a subshift ([`LanguageOn`](#obj-LanguageOn), [`MulSubshift.languageOn`](#obj-MulSubshift-languageOn)) records which local patterns on a finite window `U` actually appear in the subshift, capturing the locally observable behavior. Together, these pieces form a self-contained formalization of the standard symbolic dynamics framework — subshifts as closed shift-invariant sets, equivalently described by families of forbidden patterns — generalized to arbitrary groups and alphabets.

---

## Quick Reference

| # | Kind | Category | Name | Summary |
|---|------|----------|------|---------|
| 1 | def | 💡 Central Concept | [Left-translation shift on configurations ([`mulShift`](#obj-mulShift))](#obj-mulShift) | This defines the **left-translation shift** (multiplicative version) on configurations over a group `G` with values in `A`. |
| 2 | def | 💡 Central Concept | [Cylinder Set in Product Space ([`cylinder`](#obj-cylinder))](#obj-cylinder) | A cylinder set is the collection of all configurations `y : G → A` that agree with a fixed reference configuration `x` on every element of a finite subset `U` of the index group `G`, i.e., the set `{y \| ∀ g ∈ U, y g = x g}`. |
| 3 | lemma | 🔧 Technical Lemma | [Multiplication-Shift Evaluation Lemma ([`mulShift_apply`](#obj-mulShift_apply))](#obj-mulShift_apply) | This lemma states that applying a "multiplication-shift" map — formed by multiplying a function by a fixed group element — to an argument gives the product of the original function's value at that argument with the fixed element. |
| 4 | lemma | 🏆 Central Result | [Multiply-Shift Identity at One ([`mulShift_one`](#obj-mulShift_one))](#obj-mulShift_one) | This lemma states that applying the "multiply-shift" operation with the identity element (one) acts as the identity: shifting by multiplying with 1 leaves the argument unchanged. |
| 5 | lemma | 🏆 Central Result | [Shift composition equals multiplication ([`mulShift_mul`](#obj-mulShift_mul))](#obj-mulShift_mul) | This lemma states that composing two left-translation shifts is the same as shifting by the product: shifting a function $x : G \to A$ first by $g_1$ and then by $g_2$ equals shifting by $g_1 \cdot g_2$. |
| 6 | structure | 🏗️ Core Structure | [Subshift Structure on Alphabet ([`Subshift`](#obj-Subshift))](#obj-Subshift) | A subshift is a structure packaging a closed, shift-invariant subset of the configuration space $A^G$, where $A$ is a topological space (the alphabet) and $G$ is an additive monoid (the index group). |
| 7 | structure | 🏗️ Core Structure | [Multiplicative Subshift Structure ([`MulSubshift`](#obj-MulSubshift))](#obj-MulSubshift) | A structure packaging together a subshift with a compatible multiplicative structure. |
| 8 | structure | 🏗️ Core Structure | [Finite Configuration Pattern in Full Shift ([`Pattern`](#obj-Pattern))](#obj-Pattern) | A structure representing a finitely-supported configuration in the full shift $A^G$, where $A$ is the alphabet (with a designated default element) and $G$ is the index group or set. |
| 9 | lemma | 🏆 Central Result | [Continuity of Left-Translation Shift ([`continuous_mulShift`](#obj-continuous_mulShift))](#obj-continuous_mulShift) | This lemma states that for a topological group $G$, the map $x \mapsto g \cdot x$ (left multiplication by a fixed element $g$) is continuous as a function $G \to G$. |
| 10 | lemma | 🔧 Technical Lemma | [Cylinder Set as Restricted Pi of Singletons ([`cylinder_eq_set_pi`](#obj-cylinder_eq_set_pi))](#obj-cylinder_eq_set_pi) | This lemma establishes that a cylinder set defined by a finite set of coordinates `U` and a point `x : G → A` equals the pi-type product over `U` of singleton sets `{x i}`. |
| 11 | lemma | 🏆 Central Result | [Cylinder Membership Characterization ([`mem_cylinder`](#obj-mem_cylinder))](#obj-mem_cylinder) | A lemma characterizing when a point belongs to a cylinder set: an element `y` lies in the cylinder of `x` defined by the finite set `U` if and only if `y` agrees with `x` on every index in `U`. |
| 12 | def | 📐 Technical Definition | [Full Shift Subshift Instance ([`mulFullShift`](#obj-mulFullShift))](#obj-mulFullShift) | This definition constructs the **full shift** as a [`MulSubshift`](#obj-MulSubshift) on alphabet `A` over a monoid `G`. |
| 13 | def | 📐 Technical Definition | [Pattern from Configuration Restriction ([`fromConfig`](#obj-fromConfig))](#obj-fromConfig) | This definition extracts a finite pattern from a configuration by restricting it to a finite subset. |
| 14 | lemma | 🏆 Central Result | [Finiteness of Patterns with Fixed Support ([`finite_setOf_pattern_support_eq`](#obj-finite_setOf_pattern_support_eq))](#obj-finite_setOf_pattern_support_eq) | The set of all patterns (over a finite inhabited alphabet `A` and group `G`) whose support is exactly the finite set `U` is itself finite. |
| 15 | lemma | 🔧 Technical Lemma | [Cylinders Open in Discrete Topology ([`isOpen_cylinder`](#obj-isOpen_cylinder))](#obj-isOpen_cylinder) | When the alphabet type `A` carries the discrete topology, every cylinder set is open. |
| 16 | lemma | 🔧 Technical Lemma | [Cylinders Are Closed in T1 Spaces ([`isClosed_cylinder`](#obj-isClosed_cylinder))](#obj-isClosed_cylinder) | This lemma states that in a product space of the form $A^G$, any cylinder set is closed whenever $A$ is a T1 space. |
| 17 | def | 📐 Technical Definition | [Pattern translated to group element ([`Pattern.mulShift`](#obj-Pattern-mulShift))](#obj-Pattern-mulShift) | This is a function that takes a finite pattern `p` (a partial configuration on a group `G` with values in `A`) and a group element `v`, and produces a full configuration `G → A` where the pattern is "placed" at the translate `v`. |
| 18 | def | 📐 Technical Definition | [Language of Configurations on Shape ([`LanguageOn`](#obj-LanguageOn))](#obj-LanguageOn) | This is a definition that extracts the "local language" of a set of configurations `X` (functions from a group `G` to an alphabet `A`) restricted to a finite shape `U`. |
| 19 | def | 📐 Technical Definition | [Shift Space of Forbidden Patterns ([`mulForbidden`](#obj-mulForbidden))](#obj-mulForbidden) | This definition constructs the set of configurations (functions `G → A`) that avoid every pattern in a given forbidden family `F`. |
| 20 | lemma | 🔧 Technical Lemma | [Shifted Pattern Agrees with Original at Preimage ([`mulShift_apply_mul_left_of_mem`](#obj-mulShift_apply_mul_left_of_mem))](#obj-mulShift_apply_mul_left_of_mem) | This lemma states that when a pattern `p` is left-translated by an element `v`, the resulting shifted configuration evaluated at the translated point `v * w` recovers the original configuration value `p.config w`, provided `w` lies in the support of `p`. |
| 21 | def | 📐 Technical Definition | [Language of Subshift on Finite Shape ([`MulSubshift.languageOn`](#obj-MulSubshift-languageOn))](#obj-MulSubshift-languageOn) | The set of all patterns with shape `U` (a finite subset of the group `G`) that appear in the subshift `Y`. |
| 22 | def | 📐 Technical Definition | [Pattern Occurrence at Group Position ([`Pattern.mulOccursInAt`](#obj-Pattern-mulOccursInAt))](#obj-Pattern-mulOccursInAt) | This definition captures the notion that a finite pattern `p` appears in a configuration `x : G → A` at position `g : G`. |
| 23 | lemma | 🔧 Technical Lemma | [Occurrence Set Equals Cylinder ([`mulOccursInAt_eq_cylinder`](#obj-mulOccursInAt_eq_cylinder))](#obj-mulOccursInAt_eq_cylinder) | This lemma characterizes the **occurrence set** of a pattern `p` at position `g`: the set of all configurations `x` in which `p` occurs at position `g` is exactly the cylinder set defined by the translated support `g · (p.support)` and the shifted pattern `p.mulShift g`. |
| 24 | lemma | 🔧 Technical Lemma | [Pattern Occurrence Under Configuration Shift ([`mulOccursInAt_mulShift`](#obj-mulOccursInAt_mulShift))](#obj-mulOccursInAt_mulShift) | This lemma states that checking whether a pattern `p` occurs at position `h` in a `g`-shifted configuration is equivalent to checking whether `p` occurs at position `g * h` in the original configuration. |
| 25 | lemma | 🔧 Technical Lemma | [Open Set of Pattern Occurrences ([`isOpen_mulOccursInAt`](#obj-isOpen_mulOccursInAt))](#obj-isOpen_mulOccursInAt) | This lemma states that, when the alphabet $A$ carries the discrete topology, the set of configurations $x$ in which a given pattern $p$ occurs (via multiplication) at a fixed group element $g$ is an open set. |
| 26 | lemma | 🔧 Technical Lemma | [Shift Stability of Pattern Avoidance ([`mapsTo_mulShift_mulForbidden`](#obj-mapsTo_mulShift_mulForbidden))](#obj-mapsTo_mulShift_mulForbidden) | This lemma states that the set of configurations avoiding a given family `F` of patterns is closed under multiplication shifts. |
| 27 | lemma | 🔧 Technical Lemma | [Avoiding Patterns Is a Closed Condition ([`isClosed_mulForbidden`](#obj-isClosed_mulForbidden))](#obj-isClosed_mulForbidden) | This lemma states that when `A` carries the discrete topology, the set `mulForbidden F` of colorings `G → A` that avoid every pattern in the family `F` is a closed subset of the product topology on `G → A`. |
| 28 | def | 📐 Technical Definition | [Subshift from Forbidden Patterns ([`MulSubshift.ofForbidden`](#obj-MulSubshift-ofForbidden))](#obj-MulSubshift-ofForbidden) | This definition constructs a multiplicative subshift on configurations `G → A` by specifying a family `F` of forbidden patterns. |
| 29 | lemma | 🏆 Central Result | [Closure of Occurrence Locus ([`isClosed_mulOccursInAt`](#obj-isClosed_mulOccursInAt))](#obj-isClosed_mulOccursInAt) | This lemma states that for a pattern `p` in a topological space satisfying the T1 axiom, the set of points `x` (in the space `A`) at which the pattern `p` occurs at group element `g` via multiplication is a closed set. |

---

## Objects (Dependency Order)

<a id="obj-mulShift"></a>
### 1. Left-translation shift on configurations ([`mulShift`](#obj-mulShift)) _(lines 151–153)_

<span style="background:#f3e5f5;color:#5c1a6e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Central Concept</span>&ensp;`def`

_This defines the **left-translation shift** (multiplicative version) on configurations over a group `G` with values in `A`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def mulShift (g : G) (x : G → A) : G → A
```

This defines the **left-translation shift** (multiplicative version) on configurations over a group `G` with values in `A`. Given an element `g : G` and a configuration `x : G → A`, the shifted configuration `mulShift g x` is the function `h ↦ x (g * h)`, i.e., the value at position `h` in the new configuration equals the value of `x` at position `g * h`. Intuitively, this "pulls back" the configuration by left-multiplication by `g`, shifting the entire pattern in the direction of `g`.

</details>

---

<a id="obj-cylinder"></a>
### 2. Cylinder Set in Product Space ([`cylinder`](#obj-cylinder)) _(lines 195–200)_

<span style="background:#f3e5f5;color:#5c1a6e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Central Concept</span>&ensp;`def`

_A cylinder set is the collection of all configurations `y : G → A` that agree with a fixed reference configuration `x` on every element of a finite subset `U` of the index group `G`, i.e., the set `{y | ∀ g ∈ U, y g = x g}`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def cylinder (U : Finset G) (x : G → A) : Set (G → A)
```

A cylinder set is the collection of all configurations `y : G → A` that agree with a fixed reference configuration `x` on every element of a finite subset `U` of the index group `G`, i.e., the set `{y | ∀ g ∈ U, y g = x g}`. The remaining coordinates outside `U` are unconstrained. When `A` carries the discrete topology, cylinder sets form a basis of clopen sets for the product (Tychonoff) topology on `G → A`, making them fundamental to the study of symbolic dynamics and shift spaces.

</details>

---

<a id="obj-mulShift_apply"></a>
### 3. Multiplication-Shift Evaluation Lemma ([`mulShift_apply`](#obj-mulShift_apply)) _(lines 154–156)_

<span style="background:#fef3e2;color:#7d4e1e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Lemma</span>&ensp;`lemma`

_This lemma states that applying a "multiplication-shift" map — formed by multiplying a function by a fixed group element — to an argument gives the product of the original function's value at that argument with the fixed element._

<details>
<summary>View details</summary>

**Signature:**
```lean
@[to_additive (attr
```

This lemma states that applying a "multiplication-shift" map — formed by multiplying a function by a fixed group element — to an argument gives the product of the original function's value at that argument with the fixed element. In other words, if `f` is a function and `g` is a group element, then `(mulShift f g) x = f x * g` for all `x`. This is essentially the unfolding or definitional evaluation rule for the [`mulShift`](#obj-mulShift) construction.

</details>

---

<a id="obj-mulShift_one"></a>
### 4. Multiply-Shift Identity at One ([`mulShift_one`](#obj-mulShift_one)) _(lines 157–160)_

<span style="background:#d8f3dc;color:#1a5c2a;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Central Result</span>&ensp;`lemma`

_This lemma states that applying the "multiply-shift" operation with the identity element (one) acts as the identity: shifting by multiplying with 1 leaves the argument unchanged._

<details>
<summary>View details</summary>

**Signature:**
```lean
@[to_additive (attr
```

This lemma states that applying the "multiply-shift" operation with the identity element (one) acts as the identity: shifting by multiplying with 1 leaves the argument unchanged. It is tagged with `to_additive`, meaning an additive version (where multiplication is replaced by addition and 1 is replaced by 0) is automatically generated as a companion result.

</details>

---

<a id="obj-mulShift_mul"></a>
### 5. Shift composition equals multiplication ([`mulShift_mul`](#obj-mulShift_mul)) _(lines 161–167)_

<span style="background:#d8f3dc;color:#1a5c2a;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Central Result</span>&ensp;`lemma`

_This lemma states that composing two left-translation shifts is the same as shifting by the product: shifting a function $x : G \to A$ first by $g_1$ and then by $g_2$ equals shifting by $g_1 \cdot g_2$._

<details>
<summary>View details</summary>

**Signature:**
```lean
@[to_additive] lemma mulShift_mul (g₁ g₂ : G) (x : G → A) :
    mulShift (g₁ * g₂) x = mulShift g₂ (mulShift g₁ x)
```

This lemma states that composing two left-translation shifts is the same as shifting by the product: shifting a function $x : G \to A$ first by $g_1$ and then by $g_2$ equals shifting by $g_1 \cdot g_2$. In other words, the map $g \mapsto \text{mulShift}_g$ is a right action (or antihomomorphism) of $G$ on functions $G \to A$. The `@[to_additive]` attribute generates the additive analogue, where multiplication is replaced by addition.

</details>

---

<a id="obj-Subshift"></a>
### 6. Subshift Structure on Alphabet ([`Subshift`](#obj-Subshift)) _(lines 230–249)_

<span style="background:#fde8d8;color:#7a2000;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Core Structure</span>&ensp;`structure`

_A subshift is a structure packaging a closed, shift-invariant subset of the configuration space $A^G$, where $A$ is a topological space (the alphabet) and $G$ is an additive monoid (the index group)._

<details>
<summary>View details</summary>

**Signature:**
```lean
structure Subshift (A : Type*) [TopologicalSpace A] (G : Type*) [AddMonoid G]
```

A subshift is a structure packaging a closed, shift-invariant subset of the configuration space $A^G$, where $A$ is a topological space (the alphabet) and $G$ is an additive monoid (the index group). It consists of three components: a carrier set of allowed configurations $G \to A$, a proof that this set is closed in the product topology on $A^G$, and a proof that the set is invariant under all left-translation shifts (i.e., for each $g \in G$, the shift-by-$g$ map sends the carrier into itself).

</details>

---

<a id="obj-MulSubshift"></a>
### 7. Multiplicative Subshift Structure ([`MulSubshift`](#obj-MulSubshift)) _(lines 250–268)_

<span style="background:#fde8d8;color:#7a2000;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Core Structure</span>&ensp;`structure`

_A structure packaging together a subshift with a compatible multiplicative structure._

<details>
<summary>View details</summary>

**Signature:**
```lean
structure MulSubshift
```

A structure packaging together a subshift with a compatible multiplicative structure. It bundles a type (or set) that simultaneously carries the data of a subshift (a closed, shift-invariant subset of a full shift space) and a monoid or semigroup multiplication, such that the shift action is compatible with the multiplicative operation. This provides a unified framework for studying symbolic dynamical systems that also possess algebraic structure.

</details>

---

<a id="obj-Pattern"></a>
### 8. Finite Configuration Pattern in Full Shift ([`Pattern`](#obj-Pattern)) _(lines 286–317)_

<span style="background:#fde8d8;color:#7a2000;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Core Structure</span>&ensp;`structure`

_A structure representing a finitely-supported configuration in the full shift $A^G$, where $A$ is the alphabet (with a designated default element) and $G$ is the index group or set._

<details>
<summary>View details</summary>

**Signature:**
```lean
structure Pattern (A : Type*) (G : Type*) [Inhabited A]
```

A structure representing a finitely-supported configuration in the full shift $A^G$, where $A$ is the alphabet (with a designated default element) and $G$ is the index group or set. It packages together a global configuration `config : G → A`, a finite set `support ⊆ G`, and a proof that `config` takes the default value of $A$ at every position outside `support`. Intuitively, this encodes a partial function $G \to A$ defined on finitely many coordinates, with all unspecified positions set to the default. Patterns serve as forbidden configurations for defining subshifts, and each pattern corresponds to the cylinder set of all full configurations agreeing with `config` on `support`.

</details>

---

<a id="obj-continuous_mulShift"></a>
### 9. Continuity of Left-Translation Shift ([`continuous_mulShift`](#obj-continuous_mulShift)) _(lines 168–194)_

<span style="background:#d8f3dc;color:#1a5c2a;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Central Result</span>&ensp;`lemma`

_This lemma states that for a topological group $G$, the map $x \mapsto g \cdot x$ (left multiplication by a fixed element $g$) is continuous as a function $G \to G$._

<details>
<summary>View details</summary>

**Signature:**
```lean
@[to_additive (attr
```

This lemma states that for a topological group $G$, the map $x \mapsto g \cdot x$ (left multiplication by a fixed element $g$) is continuous as a function $G \to G$. It follows from the continuity of the group multiplication together with the fact that a constant map is continuous.

</details>

---

<a id="obj-cylinder_eq_set_pi"></a>
### 10. Cylinder Set as Restricted Pi of Singletons ([`cylinder_eq_set_pi`](#obj-cylinder_eq_set_pi)) _(lines 201–204)_

<span style="background:#fef3e2;color:#7d4e1e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Lemma</span>&ensp;`lemma`

_This lemma establishes that a cylinder set defined by a finite set of coordinates `U` and a point `x : G → A` equals the pi-type product over `U` of singleton sets `{x i}`._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma cylinder_eq_set_pi (U : Finset G) (x : G → A) :
    cylinder U x = Set.pi (↑U : Set G) (fun i => ({x i} : Set A))
```

This lemma establishes that a cylinder set defined by a finite set of coordinates `U` and a point `x : G → A` equals the pi-type product over `U` of singleton sets `{x i}`. In other words, the cylinder set consists precisely of all functions `G → A` that agree with `x` on every coordinate in `U`, which is exactly what `Set.pi U (fun i => {x i})` expresses.

</details>

---

<a id="obj-mem_cylinder"></a>
### 11. Cylinder Membership Characterization ([`mem_cylinder`](#obj-mem_cylinder)) _(lines 205–210)_

<span style="background:#d8f3dc;color:#1a5c2a;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Central Result</span>&ensp;`lemma`

_A lemma characterizing when a point belongs to a cylinder set: an element `y` lies in the cylinder of `x` defined by the finite set `U` if and only if `y` agrees with `x` on every index in `U`._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma mem_cylinder {U : Finset G} {x y : G → A} :
    y ∈ cylinder U x ↔ ∀ i ∈ U, y i = x i
```

A lemma characterizing when a point belongs to a cylinder set: an element `y` lies in the cylinder of `x` defined by the finite set `U` if and only if `y` agrees with `x` on every index in `U`. In other words, the cylinder consists precisely of all functions sharing the same values as `x` at the finitely many specified coordinates.

</details>

---

<a id="obj-mulFullShift"></a>
### 12. Full Shift Subshift Instance ([`mulFullShift`](#obj-mulFullShift)) _(lines 269–285)_

<span style="background:#f2f2f2;color:#444444;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Definition</span>&ensp;`def`

_This definition constructs the **full shift** as a [`MulSubshift`](#obj-MulSubshift) on alphabet `A` over a monoid `G`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def mulFullShift (A G) [TopologicalSpace A] [Monoid G] : MulSubshift A G where
  carrier
```

This definition constructs the **full shift** as a [`MulSubshift`](#obj-MulSubshift) on alphabet `A` over a monoid `G`. It is the subshift whose carrier set consists of *all* configurations `G → A`, i.e., no restriction is placed on which functions are allowed. This is the largest possible subshift on the given alphabet and index monoid, serving as a canonical example of a multiplicative subshift.

</details>

---

<a id="obj-fromConfig"></a>
### 13. Pattern from Configuration Restriction ([`fromConfig`](#obj-fromConfig)) _(lines 391–411)_

<span style="background:#f2f2f2;color:#444444;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Definition</span>&ensp;`def`

_This definition extracts a finite pattern from a configuration by restricting it to a finite subset._

<details>
<summary>View details</summary>

**Signature:**
```lean
noncomputable def fromConfig (x : G → A) (U : Finset G) : Pattern A G
```

This definition extracts a finite pattern from a configuration by restricting it to a finite subset. Given a configuration `x : G → A` (assigning an alphabet symbol to each group element) and a finite set `U : Finset G`, it produces a `Pattern A G` whose coordinate function agrees with `x` on elements of `U`, takes the default value of `A` outside `U`, and has support exactly `U`.

</details>

---

<a id="obj-finite_setOf_pattern_support_eq"></a>
### 14. Finiteness of Patterns with Fixed Support ([`finite_setOf_pattern_support_eq`](#obj-finite_setOf_pattern_support_eq)) _(lines 586–615)_

<span style="background:#d8f3dc;color:#1a5c2a;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Central Result</span>&ensp;`lemma`

_The set of all patterns (over a finite inhabited alphabet `A` and group `G`) whose support is exactly the finite set `U` is itself finite._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma finite_setOf_pattern_support_eq
    {A G : Type*} [Finite A] [Inhabited A]
    (U : Finset G) :
    ({p : Pattern A G | p.support = U}).Finite
```

The set of all patterns (over a finite inhabited alphabet `A` and group `G`) whose support is exactly the finite set `U` is itself finite. This follows because each such pattern is a function from `U` to `A`, and since both `U` and `A` are finite, there are only finitely many such functions.

</details>

---

<a id="obj-isOpen_cylinder"></a>
### 15. Cylinders Open in Discrete Topology ([`isOpen_cylinder`](#obj-isOpen_cylinder)) _(lines 211–215)_

<span style="background:#fef3e2;color:#7d4e1e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Lemma</span>&ensp;`lemma`

_When the alphabet type `A` carries the discrete topology, every cylinder set is open._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma isOpen_cylinder [DiscreteTopology A] (U : Finset G) (x : G → A) :
    IsOpen (cylinder U x)
```

When the alphabet type `A` carries the discrete topology, every cylinder set is open. A cylinder set is determined by specifying values of a function `G → A` on a finite set `U ⊆ G`, so this says that the set of all functions agreeing with `x` on the finitely many coordinates in `U` is an open subset of the product space `G → A`.

</details>

---

<a id="obj-isClosed_cylinder"></a>
### 16. Cylinders Are Closed in T1 Spaces ([`isClosed_cylinder`](#obj-isClosed_cylinder)) _(lines 216–229)_

<span style="background:#fef3e2;color:#7d4e1e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Lemma</span>&ensp;`lemma`

_This lemma states that in a product space of the form $A^G$, any cylinder set is closed whenever $A$ is a T1 space._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma isClosed_cylinder [T1Space A] (U : Finset G) (x : G → A) :
    IsClosed (cylinder U x)
```

This lemma states that in a product space of the form $A^G$, any cylinder set is closed whenever $A$ is a T1 space. A cylinder set `cylinder U x` is determined by specifying the values of coordinates in a finite set $U \subseteq G$ to match a given function $x : G \to A$. Since $A$ is T1, each singleton $\{x(g)\}$ is closed in $A$, and a cylinder is a finite intersection of preimages of such singletons under continuous projection maps, hence closed in the product topology.

</details>

---

<a id="obj-Pattern-mulShift"></a>
### 17. Pattern translated to group element ([`Pattern.mulShift`](#obj-Pattern-mulShift)) _(lines 373–390)_

<span style="background:#f2f2f2;color:#444444;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Definition</span>&ensp;`def`

_This is a function that takes a finite pattern `p` (a partial configuration on a group `G` with values in `A`) and a group element `v`, and produces a full configuration `G → A` where the pattern is "placed" at the translate `v`._

<details>
<summary>View details</summary>

**Signature:**
```lean
protected noncomputable def Pattern.mulShift (p : Pattern A G) (v : G) : G → A
```

This is a function that takes a finite pattern `p` (a partial configuration on a group `G` with values in `A`) and a group element `v`, and produces a full configuration `G → A` where the pattern is "placed" at the translate `v`. For an input `h : G`, if `h` lies in the left-translate `v + p.support`, the function noncomputably chooses some `w` in the support with `v + w = h` and returns `p.config w`; otherwise it returns the default value of `A`. Because no left-cancellation is assumed, the choice of preimage `w` may be non-unique, so the equation `mulShift p v (v + w) = p.config w` only holds up to a separate cancellation hypothesis proved elsewhere.

</details>

---

<a id="obj-LanguageOn"></a>
### 18. Language of Configurations on Shape ([`LanguageOn`](#obj-LanguageOn)) _(lines 616–619)_

<span style="background:#f2f2f2;color:#444444;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Definition</span>&ensp;`def`

_This is a definition that extracts the "local language" of a set of configurations `X` (functions from a group `G` to an alphabet `A`) restricted to a finite shape `U`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def LanguageOn (X : Set (G → A)) (U : Finset G) : Set (Pattern A G)
```

This is a definition that extracts the "local language" of a set of configurations `X` (functions from a group `G` to an alphabet `A`) restricted to a finite shape `U`. Specifically, it returns the set of all patterns (functions on the finite domain `U`) that arise as restrictions of some configuration `x ∈ X` to `U`. This captures which local patterns are "allowed" or "observable" within `X` on the window `U`.

</details>

---

<a id="obj-mulForbidden"></a>
### 19. Shift Space of Forbidden Patterns ([`mulForbidden`](#obj-mulForbidden)) _(lines 338–372)_

<span style="background:#f2f2f2;color:#444444;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Definition</span>&ensp;`def`

_This definition constructs the set of configurations (functions `G → A`) that avoid every pattern in a given forbidden family `F`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def mulForbidden (F : Set (Pattern A G)) : Set (G → A)
```

This definition constructs the set of configurations (functions `G → A`) that avoid every pattern in a given forbidden family `F`. Formally, a configuration `x : G → A` belongs to `mulForbidden F` if and only if no pattern `p ∈ F` occurs in `x` at any position `g : G` (where occurrence is defined via the monoid action of `G`). This is the standard construction of a **subshift**: the set of bi-infinite sequences (or higher-dimensional analogues) over alphabet `A` whose local behavior never matches any forbidden pattern.

</details>

---

<a id="obj-mulShift_apply_mul_left_of_mem"></a>
### 20. Shifted Pattern Agrees with Original at Preimage ([`mulShift_apply_mul_left_of_mem`](#obj-mulShift_apply_mul_left_of_mem)) _(lines 412–440)_

<span style="background:#fef3e2;color:#7d4e1e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Lemma</span>&ensp;`lemma`

_This lemma states that when a pattern `p` is left-translated by an element `v`, the resulting shifted configuration evaluated at the translated point `v * w` recovers the original configuration value `p.config w`, provided `w` lies in the support of `p`._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma mulShift_apply_mul_left_of_mem
    (p : Pattern A G) (v w : G) (hw : w ∈ p.support) :
    p.mulShift v (v * w) = p.config w
```

This lemma states that when a pattern `p` is left-translated by an element `v`, the resulting shifted configuration evaluated at the translated point `v * w` recovers the original configuration value `p.config w`, provided `w` lies in the support of `p`. In other words, the shift operation is consistent with the group action: `(p.mulShift v)(v * w) = p.config w`. The proof relies on left-cancellation in the group `G` to uniquely identify `w` as the preimage of `v * w` under left-multiplication by `v`.

</details>

---

<a id="obj-MulSubshift-languageOn"></a>
### 21. Language of Subshift on Finite Shape ([`MulSubshift.languageOn`](#obj-MulSubshift-languageOn)) _(lines 620–628)_

<span style="background:#f2f2f2;color:#444444;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Definition</span>&ensp;`def`

_The set of all patterns with shape `U` (a finite subset of the group `G`) that appear in the subshift `Y`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def MulSubshift.languageOn {A G} [TopologicalSpace A] [Inhabited A] [Monoid G]
    (Y : MulSubshift A G) (U : Finset G) : Set (Pattern A G)
```

The set of all patterns with shape `U` (a finite subset of the group `G`) that appear in the subshift `Y`. Concretely, it consists of all patterns over the alphabet `A` indexed by elements of `U` that are realized by some configuration in `Y`, capturing the local behavior of `Y` on the finite window `U`.

</details>

---

<a id="obj-Pattern-mulOccursInAt"></a>
### 22. Pattern Occurrence at Group Position ([`Pattern.mulOccursInAt`](#obj-Pattern-mulOccursInAt)) _(lines 318–337)_

<span style="background:#f2f2f2;color:#444444;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Definition</span>&ensp;`def`

_This definition captures the notion that a finite pattern `p` appears in a configuration `x : G → A` at position `g : G`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def Pattern.mulOccursInAt (p : Pattern A G) (x : G → A) (g : G) : Prop
```

This definition captures the notion that a finite pattern `p` appears in a configuration `x : G → A` at position `g : G`. Formally, it is the proposition that for every position `h` in the support of `p`, the configuration value `x(g + h)` equals the pattern's prescribed value `p.config(h)`. Intuitively, this says the pattern `p` is visible in `x` when you look at the "window" of positions obtained by translating the support of `p` by `g`, and it serves as the foundational notion for defining subshifts by specifying which forbidden patterns must not occur anywhere in a configuration.

</details>

---

<a id="obj-mulOccursInAt_eq_cylinder"></a>
### 23. Occurrence Set Equals Cylinder ([`mulOccursInAt_eq_cylinder`](#obj-mulOccursInAt_eq_cylinder)) _(lines 489–516)_

<span style="background:#fef3e2;color:#7d4e1e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Lemma</span>&ensp;`lemma`

_This lemma characterizes the **occurrence set** of a pattern `p` at position `g`: the set of all configurations `x` in which `p` occurs at position `g` is exactly the cylinder set defined by the translated support `g · (p.support)` and the shifted pattern `p.mulShift g`._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma mulOccursInAt_eq_cylinder
    (p : Pattern A G) (g : G) :
    { x | p.mulOccursInAt x g } = cylinder (p.support.image (g * ·)) (p.mulShift g)
```

This lemma characterizes the **occurrence set** of a pattern `p` at position `g`: the set of all configurations `x` in which `p` occurs at position `g` is exactly the cylinder set defined by the translated support `g · (p.support)` and the shifted pattern `p.mulShift g`. In other words, a configuration `x` contains pattern `p` at position `g` if and only if `x` agrees with the `g`-translate of `p` on each translated site `g * w` for `w` in the support of `p`. The proof uses the left-cancellation property of `G` to identify the relevant preimage under left-multiplication by `g`.

</details>

---

<a id="obj-mulOccursInAt_mulShift"></a>
### 24. Pattern Occurrence Under Configuration Shift ([`mulOccursInAt_mulShift`](#obj-mulOccursInAt_mulShift)) _(lines 441–454)_

<span style="background:#fef3e2;color:#7d4e1e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Lemma</span>&ensp;`lemma`

_This lemma states that checking whether a pattern `p` occurs at position `h` in a `g`-shifted configuration is equivalent to checking whether `p` occurs at position `g * h` in the original configuration._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma mulOccursInAt_mulShift {A G : Type*} [Inhabited A] [Monoid G]
    (p : Pattern A G) (x : G → A) (g h : G) :
    p.mulOccursInAt (mulShift g x) h ↔ p.mulOccursInAt x (g * h)
```

This lemma states that checking whether a pattern `p` occurs at position `h` in a `g`-shifted configuration is equivalent to checking whether `p` occurs at position `g * h` in the original configuration. In other words, shifting the entire configuration by `g` commutes with the occurrence relation: occurrences in the shifted configuration at position `h` correspond exactly to occurrences in the original configuration at the combined position `g * h`.

</details>

---

<a id="obj-isOpen_mulOccursInAt"></a>
### 25. Open Set of Pattern Occurrences ([`isOpen_mulOccursInAt`](#obj-isOpen_mulOccursInAt)) _(lines 517–531)_

<span style="background:#fef3e2;color:#7d4e1e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Lemma</span>&ensp;`lemma`

_This lemma states that, when the alphabet $A$ carries the discrete topology, the set of configurations $x$ in which a given pattern $p$ occurs (via multiplication) at a fixed group element $g$ is an open set._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma isOpen_mulOccursInAt [DiscreteTopology A] (p : Pattern A G) (g : G) :
    IsOpen { x | p.mulOccursInAt x g }
```

This lemma states that, when the alphabet $A$ carries the discrete topology, the set of configurations $x$ in which a given pattern $p$ occurs (via multiplication) at a fixed group element $g$ is an open set. Since the discrete topology makes every subset of $A$ open, the condition of matching the pattern at a specific location is determined by finitely many coordinates, making the corresponding cylinder set open in the product topology on configurations.

</details>

---

<a id="obj-mapsTo_mulShift_mulForbidden"></a>
### 26. Shift Stability of Pattern Avoidance ([`mapsTo_mulShift_mulForbidden`](#obj-mapsTo_mulShift_mulForbidden)) _(lines 455–488)_

<span style="background:#fef3e2;color:#7d4e1e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Lemma</span>&ensp;`lemma`

_This lemma states that the set of configurations avoiding a given family `F` of patterns is closed under multiplication shifts._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma mapsTo_mulShift_mulForbidden {A G : Type*} [Inhabited A] [Monoid G]
    (F : Set (Pattern A G)) (h : G) :
    Set.MapsTo (mulShift h) (mulForbidden (A
```

This lemma states that the set of configurations avoiding a given family `F` of patterns is closed under multiplication shifts. Concretely, if a configuration `x` avoids every pattern in `F` at every position, then the shifted configuration `mulShift h x` (which reassigns each position `g` the value that `x` had at position `h * g`) also avoids every pattern in `F` at every position. In other words, `mulShift h` maps `mulForbidden F` into itself.

</details>

---

<a id="obj-isClosed_mulForbidden"></a>
### 27. Avoiding Patterns Is a Closed Condition ([`isClosed_mulForbidden`](#obj-isClosed_mulForbidden)) _(lines 532–548)_

<span style="background:#fef3e2;color:#7d4e1e;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Lemma</span>&ensp;`lemma`

_This lemma states that when `A` carries the discrete topology, the set `mulForbidden F` of colorings `G → A` that avoid every pattern in the family `F` is a closed subset of the product topology on `G → A`._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma isClosed_mulForbidden [DiscreteTopology A] (F : Set (Pattern A G)) :
    IsClosed (mulForbidden F)
```

This lemma states that when `A` carries the discrete topology, the set `mulForbidden F` of colorings `G → A` that avoid every pattern in the family `F` is a closed subset of the product topology on `G → A`. The proof strategy is visible from the docstring: each set of colorings where a specific pattern occurs at a specific location is open (since `A` is discrete), so its complement is closed, and `mulForbidden F` is an intersection of such closed sets, hence closed.

</details>

---

<a id="obj-MulSubshift-ofForbidden"></a>
### 28. Subshift from Forbidden Patterns ([`MulSubshift.ofForbidden`](#obj-MulSubshift-ofForbidden)) _(lines 573–585)_

<span style="background:#f2f2f2;color:#444444;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Technical Definition</span>&ensp;`def`

_This definition constructs a multiplicative subshift on configurations `G → A` by specifying a family `F` of forbidden patterns._

<details>
<summary>View details</summary>

**Signature:**
```lean
def MulSubshift.ofForbidden [DiscreteTopology A] (F : Set (Pattern A G)) : MulSubshift A G where
  carrier
```

This definition constructs a multiplicative subshift on configurations `G → A` by specifying a family `F` of forbidden patterns. The resulting subshift consists of all configurations in which no pattern from `F` appears at any position, with the carrier being exactly the set of `F`-avoiding configurations. The structure is well-formed because shift-invariance holds (avoiding a pattern is preserved under shifts) and closedness holds because each individual occurrence set is open in the product topology (using the discrete topology on `A`), making the avoidance set closed.

</details>

---

<a id="obj-isClosed_mulOccursInAt"></a>
### 29. Closure of Occurrence Locus ([`isClosed_mulOccursInAt`](#obj-isClosed_mulOccursInAt)) _(lines 549–572)_

<span style="background:#d8f3dc;color:#1a5c2a;padding:2px 8px;border-radius:3px;font-size:0.85em;font-weight:bold">Central Result</span>&ensp;`lemma`

_This lemma states that for a pattern `p` in a topological space satisfying the T1 axiom, the set of points `x` (in the space `A`) at which the pattern `p` occurs at group element `g` via multiplication is a closed set._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma isClosed_mulOccursInAt [T1Space A] (p : Pattern A G) (g : G) :
    IsClosed { x | p.mulOccursInAt x g }
```

This lemma states that for a pattern `p` in a topological space satisfying the T1 axiom, the set of points `x` (in the space `A`) at which the pattern `p` occurs at group element `g` via multiplication is a closed set. In other words, the locus `{ x | p.mulOccursInAt x g }` is closed in `A`, relying on the T1 separation axiom to ensure that the relevant finiteness or pointwise conditions propagate to limits.

</details>

---
