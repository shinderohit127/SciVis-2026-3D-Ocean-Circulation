"""
Data access layer — OpenVisus wrappers.

Week 1-2 task: implement LLC4320Reader using openvisuspy.

Access pattern:
    from openvisuspy import LoadDataset
    db = LoadDataset("pelican://osg-htc.org/nasa/nsdf/...")
    data = db.read(field=FIELD, time=T, quality=QUALITY, z=[z0, z1])

Quality: negative int, -15 is very coarse, 0 is full resolution.

CRITICAL: ALWAYS verify grid orientation with a cartopy coastline overlay
before using any subvolume. LLC4320 raw reads may come back horizontally
flipped relative to standard lon convention (seen in Task 0).
"""
