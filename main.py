import riff
f = riff.read("test.sf2")
riff.write("o.sf2", f)
print(f)
print(riff.read("o.sf2"))
