# FDL Formatter - Remaining Tasks

## **🚧 Core Integration Tasks**

### **1. Spinner Integration (Medium Priority)**
- **File**: `suitkaise/fdl/_int/core/formatter.py` 
- **Location**: `_execute_object()` method, spinner section
- **Task**: Refactor old spinner implementation to work with new system.
- **Note**: Spinner file recovered to `setup/` directory

### **2. Format Registry System (Low Priority)**
- **File**: `suitkaise/fdl/_int/core/formatter.py`
- **Location**: `_apply_format()` method
- **Task**: Replace hardcoded "warning" example with proper registry lookup
- **Requirements**:
  - Implement format storage/retrieval system
  - Support custom named formats like `</fmt error>`, `</fmt success>`
  - Allow runtime format definition and lookup
  - Add set of hardcoded formats for users to use, led by 'sk_' (ex. sk_error, sk_warning)

### **3. Add nested collection support for debug mode**
    Right now, we don't explicitly support collections in debug mode, as we haven't implemented nested collections yet.

## **🔧 Polish Items**

### **4. Box Justification Enhancement (Low Priority)**
- **File**: `suitkaise/fdl/_int/core/formatter.py`
- **Location**: `_end_box()` method around line 840
- **Task**: Refactor box_generator.py to work with new system

### **5. Exception Class Definitions (Very Low Priority)**
- **File**: `suitkaise/fdl/_int/core/formatter.py`
- **Location**: Lines 36, 43, 50
- **Task**: Add specific behavior to exception classes
- **Current**: Just `pass` statements (functional but minimal)
- **Enhancement**: Add helpful error messages and context

## **✅ Completed Features**

**Core FDL functionality is ~95% complete:**
- ✅ All command processing (text, time, debug, box, end)
- ✅ All basic object processing (time, type objects) 
- ✅ Variable handling (Case 1: dynamic injection, Case 2: embedded FDL)
- ✅ Debug mode (complete implementation)
- ✅ State isolation for embedded FDL strings
- ✅ Raw output processing (wrapping, justification)
- ✅ Float-based timestamp system with decimal/seconds control
- ✅ Group-oriented command structure
- ✅ Setup file integration

## **🚫 Explicitly Excluded**

- **Box backgrounds**: Never implementing (user decision)
- **Table objects**: Tables are separate `fdl.Table` class, not FDL objects
- **Progress Bars**: Progress bars are separate `fdl.ProgressBar` class, not FDL objects
