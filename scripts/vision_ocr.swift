import Foundation
import Vision
import ImageIO
let args=CommandLine.arguments
if args.count<4 { fputs("usage: vision-ocr image output.json languages\n",stderr);exit(2) }
let imageURL=URL(fileURLWithPath:args[1]),outputURL=URL(fileURLWithPath:args[2])
let requested=args[3].split(separator:",").map(String.init)
var blocks:[[String:Any]]=[],warnings:[String]=[]
let passes=requested.isEmpty || requested==["auto"] ? ["auto"]:requested
for lang in passes {
 let req=VNRecognizeTextRequest();req.recognitionLevel = .accurate;req.usesLanguageCorrection=false;req.minimumTextHeight=0.002
 if lang=="auto" { req.automaticallyDetectsLanguage=true } else { req.recognitionLanguages=[lang] }
 do {
  try VNImageRequestHandler(url:imageURL,options:[:]).perform([req])
  for item in req.results ?? [] {
   guard let candidate=item.topCandidates(1).first else {continue}
   let b=item.boundingBox
   blocks.append(["text":candidate.string,"bbox":[b.minX,1-b.maxY,b.maxX,1-b.minY],"confidence":candidate.confidence,"language":lang])
  }
 } catch {warnings.append("\(lang):\(error.localizedDescription)")}
}
let result:[String:Any]=["coordinate_space":"normalized","blocks":blocks,"warnings":warnings]
try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]).write(to:outputURL,options:.atomic)
