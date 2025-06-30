# add license here

# suitkaise/skroot/skroot.py

"""
SKRoot - Smart object storage that follows your project structure

This conceptually allows you to store objects in your project structure at different 
directories, and allows these objects to be shared with subdirectories. Maps your
directory structure into a container where you can store objects that your whole directory can access,
including its subdirectories.

To use this, call SKTree.create_tree() at the start of your program.

This will:
- create SKGlobalStorages at the root of your project, and every subdirectory, as well as every
  item in said subdirectories.
- create an SKRoot, a container that resides in top level sk global storage, and SKBranches, containers
  that reside in under level storages and sync to top level storage. this 


"""
