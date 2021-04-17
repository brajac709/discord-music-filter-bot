
import abc

class AbstractDatabase(abc.ABC):
    @abc.abstractmethod
    def searchMusic(self, id):
        return []

    @abc.abstractmethod
    def addMusic(self, id, url=None, file=None):
        pass

# meant only for small scale local testing
class TextDatabase(AbstractDatabase):
    def __init__(self):
        # TODO open file etc
        self.database_file = 'database.txt'
        self.delimiter = ','


    def searchMusic(self,id):
        theMusic = []
        with open(self.database_file, 'r') as f:
            for line in f:
                ''' id, is_file, url, filecontent (probably not allow this) '''
                parts = line.split(self.delimiter)
                print(len(parts))
                if (len(parts) >= 4) and parts[0].replace("\"", "") == id:
                    print('found id')
                    print(parts[1])
                    if parts[1].replace("\"","") == "false":
                        print('not file')
                        theMusic.append({"id": id, "url": parts[2].replace("\"","") })
                    else:
                        print('file')
                        # do not support file contents yet
                        pass

        return theMusic

    def addMusic(self, id, url=None, file=None):
        # TODO add duplicate detection
        with open(self.database_file, 'w+') as f:
            f.write('"{0}","false","{1}",\n'.format(id, url))
            

# Test as main routine
if __name__ == "__main__":

    td = TextDatabase()
    import os
    if (os.path.exists(td.database_file)):
        os.remove(td.database_file)

    td.addMusic('Super Cool Song', 'https://www.youtube.com/watch?v=enYdAxVcNZA')
    
    music = td.searchMusic('Super Cool Song')
    print(music)


