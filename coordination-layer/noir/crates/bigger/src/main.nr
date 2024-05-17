fn main(x: u32, y: pub u32) {
    assert(x > y);
}

#[test]
fn test_bigger() {
    main(3, 2);
}


#[test(should_fail)]
fn test_equal() {
    main(2, 2);
}

#[test(should_fail)]
fn test_smaller() {
    main(1, 2);
}
