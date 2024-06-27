use blake2::{Blake2s256, Digest};

pub fn padded_leaves<const N: usize>(elements: &[Vec<u8>]) -> [[u8; 32]; N] {
    let mut leaves = [[0u8; 32]; N];

    for (i, element) in elements.into_iter().enumerate() {
        assert!(i < N);
        leaves[i] = leaf(element);
    }

    leaves
}

pub fn leaf(data: &[u8]) -> [u8; 32] {
    let mut hasher = Blake2s256::new();
    hasher.update(b"NOMOS_MERKLE_LEAF");
    hasher.update(data);
    hasher.finalize().into()
}

pub fn node(a: [u8; 32], b: [u8; 32]) -> [u8; 32] {
    let mut hasher = Blake2s256::new();
    hasher.update(b"NOMOS_MERKLE_NODE");
    hasher.update(a);
    hasher.update(b);
    hasher.finalize().into()
}

pub fn root<const N: usize>(elements: [[u8; 32]; N]) -> [u8; 32] {
    let n = elements.len();

    assert!(n.is_power_of_two());

    let mut nodes = elements;

    for h in (1..=n.ilog2()).rev() {
        for i in 0..2usize.pow(h - 1) {
            nodes[i] = node(nodes[i * 2], nodes[i * 2 + 1]);
        }
    }

    nodes[0]
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PathNode {
    Left([u8; 32]),
    Right([u8; 32]),
}

pub fn verify_path(leaf: [u8; 32], path: &[PathNode], root: [u8; 32]) -> bool {
    let mut computed_hash = leaf;

    for path_node in path {
        match path_node {
            PathNode::Left(sibling_hash) => {
                computed_hash = node(*sibling_hash, computed_hash);
            }
            PathNode::Right(sibling_hash) => {
                computed_hash = node(computed_hash, *sibling_hash);
            }
        }
    }

    computed_hash == root
}

pub fn path<const N: usize>(elements: [&[u8]; N], idx: usize) -> Vec<PathNode> {
    let n = elements.len();
    assert!(n.is_power_of_two());
    assert!(idx < n);

    let mut nodes = Vec::from_iter(elements.into_iter().map(leaf));
    let mut path = Vec::new();
    let mut idx = idx;

    for h in (1..=n.ilog2()).rev() {
        if idx % 2 == 0 {
            path.push(PathNode::Right(nodes[idx + 1]));
        } else {
            path.push(PathNode::Left(nodes[idx - 1]));
        }

        idx /= 2;

        for i in 0..2usize.pow(h - 1) {
            nodes[i] = node(nodes[i * 2], nodes[i * 2 + 1]);
        }
    }

    path
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn test_root_height_1() {
        let r = root::<1>(padded_leaves(&[b"sand".into()]));

        let expected = leaf(b"sand");

        assert_eq!(r, expected);
    }

    #[test]
    fn test_root_height_2() {
        let r = root::<2>(padded_leaves(&[b"desert".into(), b"sand".into()]));

        let expected = node(leaf(b"desert"), leaf(b"sand"));

        assert_eq!(r, expected);
    }

    #[test]
    fn test_root_height_3() {
        let r = root::<4>(padded_leaves(&[
            b"desert".into(),
            b"sand".into(),
            b"feels".into(),
            b"warm".into(),
        ]));

        let expected = node(
            node(leaf(b"desert"), leaf(b"sand")),
            node(leaf(b"feels"), leaf(b"warm")),
        );

        assert_eq!(r, expected);
    }

    #[test]
    fn test_root_height_4() {
        let r = root::<8>(padded_leaves(&[
            b"desert".into(),
            b"sand".into(),
            b"feels".into(),
            b"warm".into(),
            b"at".into(),
            b"night".into(),
        ]));

        let expected = node(
            node(
                node(leaf(b"desert"), leaf(b"sand")),
                node(leaf(b"feels"), leaf(b"warm")),
            ),
            node(
                node(leaf(b"at"), leaf(b"night")),
                node([0u8; 32], [0u8; 32]),
            ),
        );

        assert_eq!(r, expected);
    }

    #[test]
    fn test_path_height_1() {
        let r = root::<1>(padded_leaves(&[b"desert".into()]));

        let p = path([b"desert"], 0);
        let expected = vec![];
        assert_eq!(p, expected);
        assert!(verify_path(leaf(b"desert"), &p, r));
    }

    #[test]
    fn test_path_height_2() {
        let r = root::<2>(padded_leaves(&[b"desert".into(), b"sand".into()]));

        // --- proof for element at idx 0

        let p0 = path([b"desert", b"sand"], 0);
        let expected0 = vec![PathNode::Right(leaf(b"sand"))];
        assert_eq!(p0, expected0);
        assert!(verify_path(leaf(b"desert"), &p0, r));

        // --- proof for element at idx 1

        let p1 = path([b"desert", b"sand"], 1);
        let expected1 = vec![PathNode::Left(leaf(b"desert"))];
        assert_eq!(p1, expected1);
        assert!(verify_path(leaf(b"sand"), &p1, r));
    }

    #[test]
    fn test_path_height_3() {
        let r = root::<4>(padded_leaves(&[
            b"desert".into(),
            b"sand".into(),
            b"feels".into(),
            b"warm".into(),
        ]));

        // --- proof for element at idx 0

        let p0 = path([b"desert", b"sand", b"feels", b"warm"], 0);
        let expected0 = vec![
            PathNode::Right(leaf(b"sand")),
            PathNode::Right(node(leaf(b"feels"), leaf(b"warm"))),
        ];
        assert_eq!(p0, expected0);
        assert!(verify_path(leaf(b"desert"), &p0, r));

        // --- proof for element at idx 1

        let p1 = path([b"desert", b"sand", b"feels", b"warm"], 1);
        let expected1 = vec![
            PathNode::Left(leaf(b"desert")),
            PathNode::Right(node(leaf(b"feels"), leaf(b"warm"))),
        ];
        assert_eq!(p1, expected1);
        assert!(verify_path(leaf(b"sand"), &p1, r));

        // --- proof for element at idx 2

        let p2 = path([b"desert", b"sand", b"feels", b"warm"], 2);
        let expected2 = vec![
            PathNode::Right(leaf(b"warm")),
            PathNode::Left(node(leaf(b"desert"), leaf(b"sand"))),
        ];
        assert_eq!(p2, expected2);
        assert!(verify_path(leaf(b"feels"), &p2, r));

        // --- proof for element at idx 3

        let p3 = path([b"desert", b"sand", b"feels", b"warm"], 3);
        let expected3 = vec![
            PathNode::Left(leaf(b"feels")),
            PathNode::Left(node(leaf(b"desert"), leaf(b"sand"))),
        ];
        assert_eq!(p3, expected3);
        assert!(verify_path(leaf(b"warm"), &p3, r));
    }
}
